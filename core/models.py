import re
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('member', 'Membre'),
        ('visitor', 'Visiteur'),
        ('partner', 'Partenaire'),
        ('volunteer', 'Bénévole'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='visitor')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True, verbose_name="Pays d'origine")
    phone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    google_id = models.CharField(max_length=128, blank=True, verbose_name='Google ID')
    is_approved = models.BooleanField(default=False, verbose_name='Approuvé par admin')
    last_seen = models.DateTimeField(null=True, blank=True)

    @property
    def display_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.username

    @property
    def is_online(self):
        if not self.last_seen:
            return False
        from django.utils import timezone
        return (timezone.now() - self.last_seen).total_seconds() < 300

    @property
    def is_partner(self):
        return self.role == 'partner'

    @property
    def is_volunteer(self):
        return self.role == 'volunteer'

    @property
    def is_member(self):
        return self.role == 'member'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class PhoneVerificationCode(models.Model):
    phone = models.CharField(max_length=20, verbose_name='Téléphone')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Code OTP SMS'
        verbose_name_plural = 'Codes OTP SMS'

    def is_valid(self):
        from django.utils import timezone
        return (
            not self.is_used
            and (timezone.now() - self.created_at).total_seconds() < 600  # 10 min
        )

    def __str__(self):
        return f"{self.phone} [{self.code}]"


class VideoContent(models.Model):
    CATEGORY_CHOICES = [
        ('film', 'Film'),
        ('blog', 'Blog'),
        ('show', 'Show'),
        ('news', 'Actualités'),
        ('upcoming', 'À venir'),
    ]
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    youtube_url = models.TextField(
        verbose_name='URL ou code embed YouTube',
        help_text='Collez l\'URL YouTube (watch, youtu.be, embed) ou directement le code <iframe> fourni par YouTube.',
        blank=True,
    )
    video_file = models.FileField(
        upload_to='videos/',
        blank=True,
        null=True,
        verbose_name='Fichier vidéo',
        help_text='Formats acceptés : MP4, WebM, OGG. Laissez vide si vous utilisez une URL YouTube.',
    )
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    description = models.TextField(blank=True)
    login_required = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    _YT_PATTERNS = [
        r'youtube\.com/watch\?(?:.*&)?v=([^&\s"]+)',
        r'youtu\.be/([^?\s"]+)',
        r'youtube(?:-nocookie)?\.com/embed/([^?\s"/]+)',
        r'youtube\.com/shorts/([^?\s"]+)',
    ]

    def get_youtube_id(self):
        for pattern in self._YT_PATTERNS:
            match = re.search(pattern, self.youtube_url)
            if match:
                return match.group(1)
        return None

    def get_embed_url(self):
        yt_id = self.get_youtube_id()
        if yt_id:
            return f'https://www.youtube.com/embed/{yt_id}'
        return ''

    @property
    def is_youtube(self):
        return bool(self.youtube_url and self.get_youtube_id())

    @property
    def is_file_video(self):
        return bool(self.video_file)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vidéo'
        verbose_name_plural = 'Vidéos'


class KPI(models.Model):
    label = models.CharField(max_length=100)
    value = models.PositiveIntegerField()
    icon = models.CharField(max_length=60, default='fas fa-star',
                            help_text='Classe Font Awesome (ex: fas fa-users)')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'KPI'

    def __str__(self):
        return f"{self.label}: {self.value}"


class Testimonial(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nom')
    role = models.CharField(max_length=100, verbose_name='Rôle / Titre')
    content = models.TextField(verbose_name='Témoignage')
    avatar = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    is_approved = models.BooleanField(default=False, verbose_name='Approuvé')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Témoignage'
        verbose_name_plural = 'Témoignages'

    def __str__(self):
        return f"{self.name} — {self.role}"


class VolunteerTask(models.Model):
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('assigned', 'Assigné'),
        ('completed', 'Terminé'),
    ]
    title = models.CharField(max_length=200, verbose_name='Titre')
    description = models.TextField(verbose_name='Description')
    assigned_to = models.ForeignKey(
        'CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tasks',
        verbose_name='Assigné à'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    deadline = models.DateField(null=True, blank=True, verbose_name='Date limite')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deadline', '-created_at']
        verbose_name = 'Tâche bénévole'
        verbose_name_plural = 'Tâches bénévoles'

    def __str__(self):
        return self.title


class PartnershipRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]
    user = models.ForeignKey(
        'CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='partnership_requests'
    )
    organization_name = models.CharField(max_length=200, verbose_name="Organisation")
    contact_name = models.CharField(max_length=100, verbose_name="Nom du contact")
    contact_email = models.EmailField(verbose_name="Email")
    message = models.TextField(verbose_name="Message")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Demande de partenariat'
        verbose_name_plural = 'Demandes de partenariat'

    def __str__(self):
        return f"{self.organization_name} ({self.get_status_display()})"


class FundingProject(models.Model):
    title = models.CharField(max_length=200, verbose_name='Titre')
    description = models.TextField(verbose_name='Description')
    goal_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Objectif (FCFA)')
    raised_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                        verbose_name='Collecté (FCFA)')
    thumbnail = models.ImageField(upload_to='projects/', blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Projet de financement'
        verbose_name_plural = 'Projets de financement'

    @property
    def progress_percentage(self):
        if self.goal_amount > 0:
            return min(int((self.raised_amount / self.goal_amount) * 100), 100)
        return 0

    def __str__(self):
        return self.title


class VideoComment(models.Model):
    video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='video_comments')
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Commentaire vidéo'
        verbose_name_plural = 'Commentaires vidéos'

    def __str__(self):
        return f"{self.user.username} → {self.video.title}"


class VideoLike(models.Model):
    video = models.ForeignKey(VideoContent, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='video_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('video', 'user')
        verbose_name = 'Like vidéo'
        verbose_name_plural = 'Likes vidéos'


class ActivityReport(models.Model):
    title = models.CharField(max_length=200, verbose_name='Titre')
    report_file = models.FileField(upload_to='reports/', verbose_name='Fichier PDF')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Rapport d\'activité'
        verbose_name_plural = 'Rapports d\'activité'

    def __str__(self):
        return self.title


class CommunityMessage(models.Model):
    TYPE_TEXT     = 'text'
    TYPE_IMAGE    = 'image'
    TYPE_STICKER  = 'sticker'
    TYPE_VOICE    = 'voice'
    TYPE_VIDEO    = 'video'
    TYPE_DOCUMENT = 'document'
    MSG_TYPES = [
        (TYPE_TEXT,     'Texte'),
        (TYPE_IMAGE,    'Image'),
        (TYPE_STICKER,  'Sticker'),
        (TYPE_VOICE,    'Vocal'),
        (TYPE_VIDEO,    'Vidéo'),
        (TYPE_DOCUMENT, 'Document'),
    ]

    user          = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='community_messages')
    msg_type      = models.CharField(max_length=10, choices=MSG_TYPES, default=TYPE_TEXT)
    text          = models.TextField(max_length=2000, blank=True)
    image         = models.ImageField(upload_to='chat/images/', blank=True, null=True)
    sticker_url   = models.URLField(blank=True)
    voice_file    = models.FileField(upload_to='chat/voice/', blank=True, null=True)
    video_file    = models.FileField(upload_to='chat/videos/', blank=True, null=True)
    video_url     = models.URLField(blank=True)
    document      = models.FileField(upload_to='chat/documents/', blank=True, null=True)
    document_name = models.CharField(max_length=255, blank=True)
    is_deleted    = models.BooleanField(default=False)
    edited_at     = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Message communauté'
        verbose_name_plural = 'Messages communauté'

    @property
    def youtube_embed_url(self):
        import re
        if not self.video_url:
            return ''
        m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)', self.video_url)
        return f'https://www.youtube.com/embed/{m.group(1)}?rel=0' if m else ''

    @property
    def document_icon(self):
        ext = (self.document_name.rsplit('.', 1)[-1] if '.' in self.document_name else '').lower()
        if ext == 'pdf':
            return ('fa-file-pdf', '#ef4444')
        if ext in ('doc', 'docx'):
            return ('fa-file-word', '#3b82f6')
        return ('fa-file', '#9ca3af')

    def __str__(self):
        return f"{self.user.username} [{self.msg_type}]: {self.text[:40]}"


class DonationRecord(models.Model):
    PAYMENT_CHOICES = [
        ('wave', 'Wave CI'),
        ('orange', 'Orange Money'),
        ('mtn', 'MTN MoMo'),
        ('other', 'Autre'),
    ]
    name = models.CharField(max_length=150, verbose_name='Nom du donateur')
    email = models.EmailField(blank=True, verbose_name='Email')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Téléphone')
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='Montant (FCFA)')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='wave')
    message = models.TextField(blank=True, verbose_name='Message')
    confirmed = models.BooleanField(default=False, verbose_name='Confirmé')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Don'
        verbose_name_plural = 'Dons'

    def __str__(self):
        return f"{self.name} — {self.amount} FCFA ({self.get_payment_method_display()})"


class BlogPost(models.Model):
    CATEGORY_CHOICES = [
        ('inspiration',  'Inspiration'),
        ('actualites',   'Actualités'),
        ('temoignages',  'Témoignages'),
        ('mission',      'Mission & Actions'),
        ('education',    'Éducation'),
        ('sante',        'Santé'),
    ]

    title       = models.CharField(max_length=255, verbose_name='Titre')
    slug        = models.SlugField(max_length=255, unique=True, verbose_name='Slug URL')
    author      = models.ForeignKey(
        'CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='blog_posts', verbose_name='Auteur'
    )
    category    = models.CharField(max_length=30, choices=CATEGORY_CHOICES, verbose_name='Catégorie')
    thumbnail   = models.ImageField(upload_to='blog/', blank=True, null=True, verbose_name='Image')
    excerpt     = models.TextField(max_length=300, blank=True, verbose_name='Résumé')
    content     = models.TextField(verbose_name='Contenu')
    is_published = models.BooleanField(default=False, verbose_name='Publié')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Article de blog'
        verbose_name_plural = 'Articles de blog'

    @property
    def read_time(self):
        words = len(self.content.split())
        minutes = max(1, round(words / 200))
        return minutes

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('blog_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title


class Casting(models.Model):
    title = models.CharField(max_length=200, verbose_name='Titre')
    description = models.TextField(verbose_name='Description')
    deadline = models.DateField(verbose_name='Date limite')
    is_open = models.BooleanField(default=True, verbose_name='Ouvert')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deadline']
        verbose_name = 'Casting'
        verbose_name_plural = 'Castings'

    def __str__(self):
        return self.title


# ──────────────────────────────────────────────────────────────────────────────
# LIVE STREAMING
# ──────────────────────────────────────────────────────────────────────────────

class LiveStream(models.Model):
    PLATFORM_CHOICES = [
        ('youtube',  'YouTube Live'),
        ('facebook', 'Facebook Live'),
        ('hls',      'Flux HLS (nginx-rtmp / SRS / mediamtx)'),
    ]

    is_live     = models.BooleanField(default=False, verbose_name='En direct maintenant')
    title       = models.CharField(max_length=200, default="Children's Fruit Live", verbose_name='Titre du direct')
    description = models.TextField(blank=True, verbose_name='Description')
    platform    = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='youtube', verbose_name='Plateforme')
    stream_url  = models.TextField(blank=True, verbose_name='URL du flux',
                                   help_text='URL YouTube Live (watch/embed), URL HLS .m3u8, ou URL Facebook Live')
    started_at  = models.DateTimeField(null=True, blank=True, verbose_name='Démarré à')
    thumbnail   = models.ImageField(upload_to='livestream/', blank=True, null=True, verbose_name='Image hors-direct')

    _YT_PATTERNS = [
        r'youtube\.com/watch\?(?:.*&)?v=([^&\s"]+)',
        r'youtu\.be/([^?\s"]+)',
        r'youtube(?:-nocookie)?\.com/embed/([^?\s"/]+)',
    ]

    def get_embed_url(self):
        if not self.stream_url:
            return ''
        if self.platform == 'youtube':
            for p in self._YT_PATTERNS:
                m = re.search(p, self.stream_url)
                if m:
                    return f'https://www.youtube.com/embed/{m.group(1)}?autoplay=1'
            return self.stream_url
        return self.stream_url

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_live=True).first()

    class Meta:
        verbose_name = 'Diffusion Live'
        verbose_name_plural = 'Diffusions Live'
        ordering = ['-started_at']
        permissions = [
            ('can_manage_live', 'Peut gérer le live (contrôle & planning)'),
        ]

    def __str__(self):
        status = '🔴 EN DIRECT' if self.is_live else '⚫ Hors ligne'
        return f"{status} — {self.title}"


class EmissionSlot(models.Model):
    CATEGORY_CHOICES = [
        ('culte',        'Culte & Prière'),
        ('temoignage',   'Témoignages'),
        ('enfants',      'Programme Enfants'),
        ('enseignement', 'Enseignement Biblique'),
        ('actualites',   'Actualités & Infos'),
        ('musique',      'Louange & Musique'),
        ('special',      'Émission Spéciale'),
        ('conference',   'Conférence'),
    ]
    CATEGORY_COLORS = {
        'culte':        '#006837',
        'temoignage':   '#8b5cf6',
        'enfants':      '#f59e0b',
        'enseignement': '#3b82f6',
        'actualites':   '#ef4444',
        'musique':      '#ec4899',
        'special':      '#f7941d',
        'conference':   '#06b6d4',
    }

    title          = models.CharField(max_length=200, verbose_name="Titre de l'émission")
    date           = models.DateField(verbose_name='Date')
    start_time     = models.TimeField(verbose_name='Heure de début')
    end_time       = models.TimeField(verbose_name='Heure de fin')
    category       = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='culte', verbose_name='Catégorie')
    description    = models.TextField(blank=True, verbose_name='Description')
    presenter      = models.CharField(max_length=100, blank=True, verbose_name='Présentateur·rice')
    thumbnail      = models.ImageField(upload_to='emissions/', blank=True, null=True, verbose_name='Miniature')
    is_highlighted = models.BooleanField(default=False, verbose_name='Mise en avant')

    class Meta:
        verbose_name = 'Créneau émission'
        verbose_name_plural = 'Grille des émissions'
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.date} {self.start_time.strftime('%H:%M')} — {self.title}"

    @property
    def color(self):
        return self.CATEGORY_COLORS.get(self.category, '#006837')

    @property
    def is_on_air(self):
        from django.utils import timezone
        now = timezone.localtime()
        if self.date != now.date():
            return False
        return self.start_time <= now.time() <= self.end_time

    @property
    def duration_minutes(self):
        from datetime import datetime
        start = datetime.combine(self.date, self.start_time)
        end   = datetime.combine(self.date, self.end_time)
        return max(1, int((end - start).total_seconds() / 60))


# ──────────────────────────────────────────────────────────────────────────────
# BIBLIOTHÈQUE D'ÉTUDE
# ──────────────────────────────────────────────────────────────────────────────

class StudyCourse(models.Model):
    title       = models.CharField(max_length=255, verbose_name='Titre')
    description = models.TextField(verbose_name='Description')
    thumbnail   = models.ImageField(upload_to='courses/', blank=True, null=True, verbose_name='Miniature')
    instructor  = models.CharField(max_length=200, blank=True, verbose_name='Auteur / Formateur')
    is_published = models.BooleanField(default=False, verbose_name='Publié')
    pass_score  = models.PositiveIntegerField(default=80, verbose_name='Score de passage (/100)')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Formation'
        verbose_name_plural = 'Formations'

    @property
    def resource_count(self):
        return self.resources.count()

    @property
    def enrolled_count(self):
        return self.enrollments.count()

    def __str__(self):
        return self.title


class CourseResource(models.Model):
    TYPE_PDF   = 'pdf'
    TYPE_WORD  = 'word'
    TYPE_VIDEO = 'video'
    TYPE_AUDIO = 'audio'
    RESOURCE_TYPES = [
        (TYPE_PDF,   'Document PDF'),
        (TYPE_WORD,  'Document Word'),
        (TYPE_VIDEO, 'Vidéo'),
        (TYPE_AUDIO, 'Audio / Podcast'),
    ]

    _YT_PATTERNS = [
        r'youtube\.com/watch\?(?:.*&)?v=([^&\s"]+)',
        r'youtu\.be/([^?\s"]+)',
        r'youtube(?:-nocookie)?\.com/embed/([^?\s"/]+)',
    ]

    course        = models.ForeignKey(StudyCourse, on_delete=models.CASCADE, related_name='resources')
    title         = models.CharField(max_length=255, verbose_name='Titre')
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPES, verbose_name='Type')
    file          = models.FileField(upload_to='course_resources/', blank=True, null=True, verbose_name='Fichier')
    video_url     = models.TextField(blank=True, verbose_name='URL Vidéo (YouTube ou lien direct)')
    description   = models.TextField(blank=True, verbose_name='Description')
    order         = models.PositiveIntegerField(default=0, verbose_name='Ordre')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Ressource de formation'
        verbose_name_plural = 'Ressources de formation'

    @property
    def icon(self):
        icons = {
            self.TYPE_PDF:   'fa-file-pdf',
            self.TYPE_WORD:  'fa-file-word',
            self.TYPE_VIDEO: 'fa-film',
            self.TYPE_AUDIO: 'fa-headphones',
        }
        return icons.get(self.resource_type, 'fa-file')

    @property
    def icon_color(self):
        colors = {
            self.TYPE_PDF:   '#ef4444',
            self.TYPE_WORD:  '#3b82f6',
            self.TYPE_VIDEO: '#f7941d',
            self.TYPE_AUDIO: '#8b5cf6',
        }
        return colors.get(self.resource_type, '#9ca3af')

    def file_extension(self):
        if self.file and self.file.name:
            return self.file.name.rsplit('.', 1)[-1].lower() if '.' in self.file.name else ''
        return ''

    def is_youtube_video(self):
        return self.resource_type == self.TYPE_VIDEO and bool(self.get_youtube_id())

    def get_youtube_id(self):
        if not self.video_url:
            return None
        for p in self._YT_PATTERNS:
            m = re.search(p, self.video_url)
            if m:
                return m.group(1)
        return None

    def get_embed_url(self):
        yt_id = self.get_youtube_id()
        if yt_id:
            return f'https://www.youtube-nocookie.com/embed/{yt_id}'
        return self.video_url

    def __str__(self):
        return f"{self.course.title} — {self.title}"


class CourseEnrollment(models.Model):
    user         = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='enrollments')
    course       = models.ForeignKey(StudyCourse, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at  = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-enrolled_at']
        verbose_name = "Inscription à une formation"
        verbose_name_plural = "Inscriptions aux formations"

    @property
    def is_completed(self):
        return self.completed_at is not None

    @property
    def progress_pct(self):
        total = self.course.resources.count()
        if total == 0:
            return 0
        done = ResourceProgress.objects.filter(
            user=self.user, resource__course=self.course, completed=True
        ).count()
        return int((done / total) * 100)

    def __str__(self):
        return f"{self.user.username} → {self.course.title}"


class ResourceProgress(models.Model):
    user         = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='resource_progress')
    resource     = models.ForeignKey(CourseResource, on_delete=models.CASCADE, related_name='progress')
    completed    = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'resource')
        verbose_name = 'Progression ressource'
        verbose_name_plural = 'Progressions ressources'

    def __str__(self):
        return f"{self.user.username} — {self.resource.title}: {'✓' if self.completed else '○'}"


class Quiz(models.Model):
    resource           = models.OneToOneField(CourseResource, on_delete=models.CASCADE, related_name='quiz', null=True, blank=True)
    course             = models.OneToOneField(StudyCourse, on_delete=models.CASCADE, related_name='final_exam', null=True, blank=True)
    title              = models.CharField(max_length=255, verbose_name='Titre')
    pass_score         = models.PositiveIntegerField(default=80, verbose_name='Score de passage (/100)')
    time_limit_minutes = models.PositiveIntegerField(default=0, verbose_name='Limite de temps (0 = illimité)')

    class Meta:
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quiz'

    @property
    def question_count(self):
        return self.questions.count()

    def __str__(self):
        if self.resource:
            return f"Quiz: {self.resource.title}"
        if self.course:
            return f"Examen final: {self.course.title}"
        return self.title


class QuizQuestion(models.Model):
    quiz        = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text        = models.TextField(verbose_name='Question')
    explanation = models.TextField(blank=True, verbose_name='Explication de la réponse correcte')
    order       = models.PositiveIntegerField(default=0)
    points      = models.PositiveIntegerField(default=1, verbose_name='Points')

    class Meta:
        ordering = ['order']
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'

    def __str__(self):
        return f"Q{self.order}: {self.text[:80]}"


class QuizChoice(models.Model):
    question   = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='choices')
    text       = models.CharField(max_length=500, verbose_name='Réponse')
    is_correct = models.BooleanField(default=False, verbose_name='Correcte')
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Choix de réponse'
        verbose_name_plural = 'Choix de réponses'

    def __str__(self):
        return f"{'✓' if self.is_correct else '✗'} {self.text[:60]}"


class QuizAttempt(models.Model):
    user         = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz         = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score        = models.FloatField(default=0)
    passed       = models.BooleanField(default=False)
    started_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Tentative de quiz'
        verbose_name_plural = 'Tentatives de quiz'

    def calculate_score(self):
        total_points = sum(q.points for q in self.quiz.questions.all())
        if total_points == 0:
            return 0
        earned = sum(
            a.question.points
            for a in self.answers.select_related('selected_choice', 'question').all()
            if a.selected_choice and a.selected_choice.is_correct
        )
        self.score = round((earned / total_points) * 100, 1)
        self.passed = self.score >= self.quiz.pass_score
        return self.score

    def __str__(self):
        return f"{self.user.username} — {self.quiz.title}: {self.score}/100"


class QuizAnswer(models.Model):
    attempt         = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question        = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(QuizChoice, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('attempt', 'question')
        verbose_name = 'Réponse'
        verbose_name_plural = 'Réponses'

    def __str__(self):
        return f"Attempt {self.attempt_id} — Q{self.question.order}"


class Certificate(models.Model):
    user               = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='certificates')
    course             = models.ForeignKey(StudyCourse, on_delete=models.CASCADE, related_name='certificates')
    attempt            = models.ForeignKey(QuizAttempt, on_delete=models.SET_NULL, null=True, blank=True)
    issued_at          = models.DateTimeField(auto_now_add=True)
    certificate_number = models.CharField(max_length=20, unique=True, blank=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-issued_at']
        verbose_name = 'Certificat'
        verbose_name_plural = 'Certificats'

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            import uuid
            self.certificate_number = f"CF-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Certificat {self.certificate_number} — {self.user.username} — {self.course.title}"
