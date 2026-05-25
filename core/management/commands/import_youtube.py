import json
import urllib.request
import urllib.parse
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.conf import settings
from core.models import VideoContent

# Mots-clés dans le nom de la playlist → catégorie sur le site
PLAYLIST_CATEGORY_MAP = {
    'film': 'film',
    'films': 'film',
    'cinéma': 'film',
    'cinema': 'film',
    'movie': 'film',
    'movies': 'film',
    'court-métrage': 'film',
    'court métrage': 'film',
    'show': 'show',
    'shows': 'show',
    'émission': 'show',
    'emission': 'show',
    'programme': 'show',
    'blog': 'blog',
    'vlog': 'blog',
    'actualité': 'news',
    'actualités': 'news',
    'actualite': 'news',
    'actualites': 'news',
    'news': 'news',
    'info': 'news',
    'infos': 'news',
    'à venir': 'upcoming',
    'a venir': 'upcoming',
    'upcoming': 'upcoming',
    'bientôt': 'upcoming',
    'bientot': 'upcoming',
    'prochainement': 'upcoming',
}


class Command(BaseCommand):
    help = 'Importe toutes les vidéos de la chaîne YouTube @CFRUIT24 dans la WebTV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--channel',
            default='@CFRUIT24',
            help='Handle ou ID de la chaîne YouTube (défaut: @CFRUIT24)',
        )
        parser.add_argument(
            '--default-category',
            default='news',
            choices=[c[0] for c in VideoContent.CATEGORY_CHOICES],
            help='Catégorie par défaut (défaut: news)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simuler sans rien sauvegarder',
        )
        parser.add_argument(
            '--no-thumbnails',
            action='store_true',
            help='Ne pas télécharger les miniatures',
        )
        parser.add_argument(
            '--login-required',
            action='store_true',
            default=False,
            help='Exiger une connexion pour regarder (défaut: non)',
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, 'YOUTUBE_API_KEY', '').strip()
        if not api_key:
            raise CommandError(
                'YOUTUBE_API_KEY manquant dans .env\n'
                'Ajoutez : YOUTUBE_API_KEY=votre_cle_api'
            )

        handle = options['channel']
        default_cat = options['default_category']
        dry_run = options['dry_run']
        no_thumbs = options['no_thumbnails']
        login_req = options['login_required']

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '[DRY-RUN] Simulation - aucune donnee ne sera sauvegardee.\n'
            ))

        # ── 1. ID de la chaîne ────────────────────────────────────
        self.stdout.write(f'[1/4] Recherche de la chaine {handle}...')
        channel_id, uploads_pl_id = self._get_channel_info(handle, api_key)
        self.stdout.write(self.style.SUCCESS(f'      Chaine trouvee : {channel_id}'))

        # ── 2. Mapping playlists → catégories ────────────────────
        self.stdout.write('[2/4] Analyse des playlists...')
        video_cats = self._build_video_categories(channel_id, api_key, default_cat)
        self.stdout.write(f'      {len(video_cats)} video(s) pre-categorisee(s) via playlists.')

        # ── 3. Toutes les vidéos de la chaîne ────────────────────
        self.stdout.write('[3/4] Recuperation de toutes les videos...')
        videos = self._get_all_videos(uploads_pl_id, api_key)
        self.stdout.write(f'      {len(videos)} video(s) trouvee(s) sur la chaine.\n')

        # ── 4. Import ─────────────────────────────────────────────
        created = skipped = errors = 0

        for item in videos:
            video_id = item['contentDetails']['videoId']
            snippet = item['snippet']
            title = snippet.get('title', '').strip()
            description = snippet.get('description', '').strip()

            if title in ('Deleted video', 'Private video', ''):
                skipped += 1
                continue

            youtube_url = f'https://www.youtube.com/watch?v={video_id}'
            category = video_cats.get(video_id, default_cat)

            thumbnail_url = (
                snippet.get('thumbnails', {}).get('maxres', {}).get('url')
                or snippet.get('thumbnails', {}).get('high', {}).get('url')
                or snippet.get('thumbnails', {}).get('medium', {}).get('url')
                or f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg'
            )

            # Déjà importé ?
            if VideoContent.objects.filter(youtube_url__icontains=video_id).exists():
                self.stdout.write(f'  [SKIP] [{category}] {title[:65]}')
                skipped += 1
                continue

            self.stdout.write(f'  [+]    [{category}] {title[:65]}')

            if not dry_run:
                try:
                    obj = VideoContent(
                        title=title,
                        youtube_url=youtube_url,
                        category=category,
                        description=description[:5000],
                        login_required=login_req,
                        is_featured=False,
                    )
                    obj.save()

                    if not no_thumbs:
                        self._fetch_thumbnail(obj, thumbnail_url, video_id)

                    created += 1
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f'    [ERREUR] {exc}'))
                    errors += 1
            else:
                created += 1

        # Resume
        self.stdout.write('\n' + '-' * 55)
        self.stdout.write(self.style.SUCCESS(f'[OK]   Importees  : {created}'))
        self.stdout.write(self.style.WARNING(f'[SKIP] Ignorees   : {skipped}'))
        if errors:
            self.stdout.write(self.style.ERROR(f'[ERR]  Erreurs    : {errors}'))
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY-RUN : relancez sans --dry-run pour importer reellement.'))

    # ── Helpers ───────────────────────────────────────────────────

    def _api_get(self, endpoint, api_key, params):
        params['key'] = api_key
        url = endpoint + '?' + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise CommandError(f'Erreur API YouTube {e.code} : {body[:300]}')

    def _get_channel_info(self, handle, api_key):
        if handle.startswith('@'):
            params = {'forHandle': handle, 'part': 'contentDetails,snippet'}
        elif handle.startswith('UC'):
            params = {'id': handle, 'part': 'contentDetails,snippet'}
        else:
            params = {'forUsername': handle, 'part': 'contentDetails,snippet'}

        data = self._api_get(
            'https://www.googleapis.com/youtube/v3/channels', api_key, params
        )
        if not data.get('items'):
            raise CommandError(
                f'Chaîne introuvable : {handle}\n'
                'Vérifiez le handle ou l\'ID de la chaîne.'
            )
        item = data['items'][0]
        channel_id = item['id']
        uploads_id = item['contentDetails']['relatedPlaylists']['uploads']
        self.stdout.write(f'   Nom : {item["snippet"]["title"]}')
        return channel_id, uploads_id

    def _build_video_categories(self, channel_id, api_key, default_cat):
        """Construit video_id → catégorie depuis les playlists de la chaîne."""
        video_cats = {}

        # Récupérer toutes les playlists
        playlists = {}
        page_token = None
        while True:
            params = {'channelId': channel_id, 'part': 'snippet', 'maxResults': 50}
            if page_token:
                params['pageToken'] = page_token
            data = self._api_get(
                'https://www.googleapis.com/youtube/v3/playlists', api_key, params
            )
            for pl in data.get('items', []):
                pl_id = pl['id']
                pl_name = pl['snippet']['title'].lower().strip()
                for keyword, cat in PLAYLIST_CATEGORY_MAP.items():
                    if keyword in pl_name:
                        playlists[pl_id] = (cat, pl['snippet']['title'])
                        self.stdout.write(
                            f'   Playlist "{pl["snippet"]["title"]}" -> [{cat}]'
                        )
                        break
            page_token = data.get('nextPageToken')
            if not page_token:
                break

        # Pour chaque playlist mappée, récupérer les vidéos
        for pl_id, (cat, pl_name) in playlists.items():
            pl_page = None
            while True:
                params = {
                    'playlistId': pl_id,
                    'part': 'contentDetails',
                    'maxResults': 50,
                }
                if pl_page:
                    params['pageToken'] = pl_page
                data = self._api_get(
                    'https://www.googleapis.com/youtube/v3/playlistItems', api_key, params
                )
                for item in data.get('items', []):
                    video_cats[item['contentDetails']['videoId']] = cat
                pl_page = data.get('nextPageToken')
                if not pl_page:
                    break

        return video_cats

    def _get_all_videos(self, uploads_pl_id, api_key):
        """Récupère toutes les vidéos de la playlist uploads (toutes les pages)."""
        videos = []
        page_token = None
        while True:
            params = {
                'playlistId': uploads_pl_id,
                'part': 'snippet,contentDetails',
                'maxResults': 50,
            }
            if page_token:
                params['pageToken'] = page_token
            data = self._api_get(
                'https://www.googleapis.com/youtube/v3/playlistItems', api_key, params
            )
            videos.extend(data.get('items', []))
            page_token = data.get('nextPageToken')
            if not page_token:
                break
        return videos

    def _fetch_thumbnail(self, video_obj, thumbnail_url, video_id):
        """Télécharge et sauvegarde la miniature YouTube."""
        try:
            with urllib.request.urlopen(thumbnail_url, timeout=15) as resp:
                data = resp.read()
            ext = thumbnail_url.split('?')[0].rsplit('.', 1)[-1] or 'jpg'
            filename = f'yt_{video_id}.{ext}'
            video_obj.thumbnail.save(filename, ContentFile(data), save=True)
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f'    ⚠ Miniature non téléchargée : {exc}'))
