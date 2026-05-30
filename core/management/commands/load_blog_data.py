import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files import File
from django.conf import settings


ARTICLES = [
    {
        "title": "Concert Children’s Fruit 2019 — Louange, Musique et Évangélisation",
        "slug": "concert-childrens-fruit-2019",
        "category": "actualites",
        "thumbnail_static": "blog/concert-2019-thumb.jpg",
        "excerpt": "Retour sur le premier Concert Annuel de Children’s Fruit en 2019 — une soirée de louange, de musique et d’évangélisation qui a rassemblé toute la communauté autour d’une même foi.",
        "content": """<style>
.cf-gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem;margin:1.5rem 0 2rem;}
.cf-gal-item{border-radius:12px;overflow:hidden;background:#f1f3f5;box-shadow:0 2px 12px rgba(0,0,0,.08);transition:.2s;}
.cf-gal-item:hover{transform:translateY(-3px);box-shadow:0 6px 24px rgba(0,0,0,.15);}
.cf-gal-item img{width:100%;height:220px;object-fit:cover;display:block;}
.cf-gal-caption{font-size:.75rem;color:#555;padding:.5rem .75rem;margin:0;line-height:1.4;background:#fff;}
.event-badge{display:inline-block;background:linear-gradient(135deg,#006837,#009450);color:#fff;font-size:.75rem;font-weight:700;padding:.3rem .9rem;border-radius:20px;margin-bottom:1.5rem;letter-spacing:.5px;}
.ticket-card{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;border-radius:16px;padding:1.5rem 2rem;margin:2rem 0;display:flex;flex-wrap:wrap;gap:1.5rem;align-items:center;}
.ticket-card .tick-item{display:flex;align-items:center;gap:.5rem;font-size:.88rem;}
.ticket-card .tick-item i{color:#f7941d;font-size:1rem;}
.people-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem;margin:1.5rem 0;}
.person-card{background:#f8f9fa;border-radius:12px;padding:1rem;text-align:center;border-top:3px solid #006837;}
.person-card .person-role{font-size:.72rem;color:#006837;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:.25rem;}
.person-card .person-name{font-size:.92rem;font-weight:700;color:#1a1a1a;}
</style>

<span class="event-badge"><i class="fas fa-music" style="margin-right:.4rem;"></i>Concert Annuel 2019</span>

<p>Le premier grand <strong>Concert Annuel de Children’s Fruit</strong> a marqué les esprits en 2019. Une soirée de louange, d’adoration et d’évangélisation rassemblant la communauté chrétienne dans un élan collectif pour célébrer la foi et transformer des vies.</p>

<div class="ticket-card">
  <div class="tick-item"><i class="fas fa-calendar-alt"></i><div><div style="font-size:.7rem;opacity:.6;text-transform:uppercase;letter-spacing:.5px;">Date</div><strong>2019</strong></div></div>
  <div class="tick-item"><i class="fas fa-map-marker-alt"></i><div><div style="font-size:.7rem;opacity:.6;text-transform:uppercase;letter-spacing:.5px;">Lieu</div><strong>Côte d’Ivoire</strong></div></div>
  <div class="tick-item"><i class="fas fa-users"></i><div><div style="font-size:.7rem;opacity:.6;text-transform:uppercase;letter-spacing:.5px;">Format</div><strong>Concert &amp; Évangélisation</strong></div></div>
  <div class="tick-item"><i class="fas fa-cross"></i><div><div style="font-size:.7rem;opacity:.6;text-transform:uppercase;letter-spacing:.5px;">Mission</div><strong>Transformer des vies</strong></div></div>
</div>

<h2><i class="fas fa-images" style="color:#006837;margin-right:.5rem;"></i>Phase Préparatoire</h2>

<p>Avant le grand soir, l’équipe de Children’s Fruit a consacré de nombreuses heures à la préparation : répétitions, prière, organisation logistique. Ces coulisses témoignent de la dévotion et de l’engagement de chaque membre.</p>

<div class="cf-gallery">
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/prep_01.jpg" alt="Préparatifs concert 2019" loading="lazy"><p class="cf-gal-caption">Préparatifs et organisation</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/prep_02.jpg" alt="Répétitions avant le concert" loading="lazy"><p class="cf-gal-caption">Répétitions de l’équipe</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/prep_03.jpg" alt="L’équipe en coulisses" loading="lazy"><p class="cf-gal-caption">L’équipe en coulisses</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/prep_04.jpg" alt="Moment de prière" loading="lazy"><p class="cf-gal-caption">Moment de prière et de communion</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/prep_05.jpg" alt="Préparation scénique" loading="lazy"><p class="cf-gal-caption">Mise en place de la scène</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/prep_06.jpg" alt="L’équipe unie" loading="lazy"><p class="cf-gal-caption">Unité et communion fraternelle</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/prep_07.jpg" alt="Répétitions finales" loading="lazy"><p class="cf-gal-caption">Répétitions de dernière minute</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/prep_08.jpg" alt="Coordination équipe" loading="lazy"><p class="cf-gal-caption">Coordination de l’équipe technique</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/prep_09.jpg" alt="Préparation finale" loading="lazy"><p class="cf-gal-caption">Les derniers préparatifs</p></div>
</div>

<h2><i class="fas fa-star" style="color:#f7941d;margin-right:.5rem;"></i>Le Concert</h2>

<p>La soirée du concert a été un moment de grâce et de célébration. Portés par la musique et la louange, les participants ont vécu une expérience spirituelle profonde. Children’s Fruit a démontré que l’art peut être un puissant vecteur d’évangélisation.</p>

<div class="cf-gallery">
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/concert_01.jpg" alt="Concert Children’s Fruit 2019" loading="lazy"><p class="cf-gal-caption">L’ambiance lors du concert</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/concert_02.jpg" alt="Performance sur scène" loading="lazy"><p class="cf-gal-caption">Performance sur scène</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/concert_03.jpg" alt="Moments de louange" loading="lazy"><p class="cf-gal-caption">Moments de louange collective</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/concert_04.jpg" alt="L’équipe sur scène" loading="lazy"><p class="cf-gal-caption">L’équipe unie sur scène</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/concert_05.jpg" alt="Concert en pleine communion" loading="lazy"><p class="cf-gal-caption">Une communion profonde avec le public</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/concert_06.jpg" alt="Finale du concert 2019" loading="lazy"><p class="cf-gal-caption">La finale du concert</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2019/concert_07.jpg" alt="Clôture du concert" loading="lazy"><p class="cf-gal-caption">Clôture en beauté</p></div>
</div>

<h2><i class="fas fa-users" style="color:#006837;margin-right:.5rem;"></i>L’Équipe</h2>

<div class="people-grid">
  <div class="person-card"><div class="person-role">Président</div><div class="person-name">Papa ALEX</div></div>
  <div class="person-card"><div class="person-role">Fondateur</div><div class="person-name">Papa RANCY KAIZER</div></div>
  <div class="person-card"><div class="person-role">Dir. Évangélisation</div><div class="person-name">Papa AUGUSTIN</div></div>
  <div class="person-card"><div class="person-role">Chef Production</div><div class="person-name">Frère KINGSLEY</div></div>
</div>

<blockquote style="border-left:4px solid #006837;padding:1rem 1.5rem;background:rgba(0,104,55,.04);border-radius:0 12px 12px 0;margin:2rem 0;">
  <p style="margin:0;font-style:italic;color:#333;font-size:1.05rem;">“Children’s Fruit — là où la musique rencontre la foi pour transformer des vies et bâtir un avenir meilleur.”</p>
</blockquote>

<p>Ce premier concert a posé les bases d’une tradition qui continue de grandir. Chaque année, Children’s Fruit revient avec plus de force, plus d’amour et plus de détermination pour servir Dieu et la communauté.</p>""",
        "is_published": True,
    },
    {
        "title": "Concert Children’s Fruit 2020 : « Choisi la Vie » — VBS, Évangélisation et Gloire",
        "slug": "concert-childrens-fruit-2020",
        "category": "actualites",
        "thumbnail_static": "blog/concert-2020-thumb.jpg",
        "excerpt": "Retour complet sur le 2e concert de Children’s Fruit (4 août 2019, Université FATEAC) : programme VBS, deux séances d’evangélisation dont un bus SOTRA, deux tenues scéniques, et la voix d’une communauté unie sous le theme « Choisi la Vie » — Deutéronome 30:18-20.",
        "content": """<style>
.cf-gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem;margin:1.5rem 0 2rem;}
.cf-gal-item{border-radius:12px;overflow:hidden;background:#f1f3f5;box-shadow:0 2px 12px rgba(0,0,0,.08);transition:.2s;}
.cf-gal-item:hover{transform:translateY(-3px);box-shadow:0 6px 24px rgba(0,0,0,.15);}
.cf-gal-item img{width:100%;height:220px;object-fit:cover;display:block;}
.cf-gal-caption{font-size:.75rem;color:#555;padding:.5rem .75rem;margin:0;line-height:1.4;background:#fff;}
.cf-ticket{background:linear-gradient(135deg,#1e1b4b,#312e81);color:#fff;border-radius:16px;padding:1.5rem;margin:2rem 0;text-align:center;}
.cf-ticket .date{font-size:1.4rem;font-weight:800;color:#fbbf24;}
.cf-ticket .lieu{font-size:.95rem;opacity:.85;margin-top:.25rem;}
.cf-ticket .theme{font-size:1.05rem;font-style:italic;margin-top:.75rem;border-top:1px solid rgba(255,255,255,.2);padding-top:.75rem;}
.cf-person{display:flex;align-items:center;gap:.75rem;padding:.75rem 1rem;background:#f8f9fa;border-radius:10px;margin-bottom:.5rem;}
.cf-person-icon{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#006837,#009450);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;flex-shrink:0;}
</style>

<p class="lead-text" style="font-size:1.15rem;line-height:1.8;font-weight:500;color:#1a1a2e;border-left:4px solid #006837;padding-left:1.25rem;margin-bottom:2rem;">
  Le <strong>4 août 2019</strong>, Children’s Fruit organisait son <strong>deuxième grand concert live de louange et d’adoration</strong> à l’Université FATEAC sise à M’Pouto. Un événement né au cœur d’un programme VBS intense, porté par une communauté de foi, de chant et d’évangélisation.
</p>

<div class="cf-ticket">
  <div style="font-size:.8rem;text-transform:uppercase;letter-spacing:1px;opacity:.7;margin-bottom:.5rem;">Grand Concert Live de Louange et d’Adoration</div>
  <div class="date">Dimanche 04 Août 2019 — 14h30 à 18h30</div>
  <div class="lieu">Université FATEAC · M’Pouto · Ticket : 2000 F CFA</div>
  <div class="theme">Thème : <strong>« CHOISI LA VIE »</strong> — Deutéronome 30 : 18-20</div>
</div>

<h2 style="font-size:1.6rem;font-weight:800;color:#006837;border-bottom:3px solid #F7941D;padding-bottom:.5rem;margin-bottom:1.5rem;">
  Phase 1 — Le Programme VBS : La Source de Tout
</h2>

<p>Tout a commencé par le <strong>VBS (Vacation Bible School)</strong>, du <strong>lundi 29 juillet au 5 août 2019</strong>. Pendant cette semaine intense, les jeunes de Children’s Fruit se sont réunis pour apprendre, grandir dans la foi et préparer quelque chose d’exceptionnel.</p>

<div class="cf-gallery">
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/prep_01.jpg" alt="Répétition dans l’église" loading="lazy"><p class="cf-gal-caption">Répétition dans l’église — les jeunes devant la croix</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/prep_02.jpg" alt="Session vocale" loading="lazy"><p class="cf-gal-caption">Session vocale — direction et écoute attentive</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/prep_03.jpg" alt="Moment de complicité" loading="lazy"><p class="cf-gal-caption">Moment de complicité entre répétitions</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/prep_04.jpg" alt="Le groupe en session" loading="lazy"><p class="cf-gal-caption">Le groupe en pleine session de travail</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/prep_05.jpg" alt="Concentration maximale" loading="lazy"><p class="cf-gal-caption">Concentration maximale avant le grand jour</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/prep_06.jpg" alt="Les jeunes talents" loading="lazy"><p class="cf-gal-caption">Les jeunes talents de Children’s Fruit</p></div>
</div>

<h3>Deux séances d’évangélisation</h3>

<div style="background:rgba(0,104,55,.06);border-radius:14px;padding:1.25rem 1.5rem;margin:1.25rem 0;">
  <p style="margin:0;"><strong style="color:#006837;">1ère évangélisation — En plein air :</strong> Sous la conduite du frère <strong>Jerry Kaizer</strong>, l’équipe est allée à la rencontre des gens dans les rues, distribuant des tracts et partageant l’Évangile.</p>
</div>

<div style="background:rgba(247,148,29,.08);border-radius:14px;padding:1.25rem 1.5rem;margin:1.25rem 0;">
  <p style="margin:0;"><strong style="color:#b45309;">2ème évangélisation — Dans un bus SOTRA :</strong> Une expérience unique et audacieuse ! L’équipe a emprunté un bus au <em>Carrefour la Vie</em> et a chanté et évangélisé les voyageurs dans le bus de la SOTRA.</p>
</div>

<blockquote style="background:rgba(0,104,55,.06);border-left:4px solid #006837;padding:1rem 1.5rem;border-radius:0 12px 12px 0;margin:1.75rem 0;font-style:italic;color:#333;">
  « Malgré les difficultés, nous y sommes arrivés dans la prière et par la grâce de notre Seigneur Jésus si merveilleux. »
  <footer style="margin-top:.5rem;font-size:.85rem;color:#666;font-style:normal;">— Rapport officiel du concert Children’s Fruit 2019</footer>
</blockquote>

<h2 style="font-size:1.6rem;font-weight:800;color:#006837;border-bottom:3px solid #F7941D;padding-bottom:.5rem;margin-bottom:1.5rem;margin-top:3rem;">
  Phase 2 — Le Concert Final : « Devant le Trône, Choisi la Vie »
</h2>

<p>Le 4 août 2019, la salle de l’Université FATEAC se transformait. Les voilages jaunes et dorés habillaient la scène. Sur le fond de scène, les mots <strong>« DEVANT LE TRÔNE — CHOISI LA VIE »</strong> résonnaient comme une invitation spirituelle.</p>

<h3>Deux tenues, une seule identité</h3>
<ul style="line-height:2;padding-left:1.25rem;">
  <li><strong>Première tenue — Les tee-shirts blancs :</strong> Symbole de pureté et d’unité.</li>
  <li><strong>Deuxième tenue — Les pagnes africains :</strong> Robes et ensembles noirs garnis de motifs kente colorés — un hommage à l’identité africaine.</li>


<div class="cf-gallery">
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/concert_01.jpg" alt="La salle FATEAC" loading="lazy"><p class="cf-gal-caption">La salle de l'Université FATEAC habillée de jaune</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/concert_02.jpg" alt="Les artistes en tenues africaines" loading="lazy"><p class="cf-gal-caption">Les artistes en tenues africaines avant la montée sur scène</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/concert_03.jpg" alt="Les jeunes au micro" loading="lazy"><p class="cf-gal-caption">Les jeunes au micro</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/concert_04.jpg" alt="Le choeur en action" loading="lazy"><p class="cf-gal-caption">Le chœur en action</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/concert_05.jpg" alt="Photo de groupe finale" loading="lazy"><p class="cf-gal-caption">Photo de groupe finale sur scène</p></div>
  <div class="cf-gal-item"><img src="/static/blog/concert-2020/concert_06.jpg" alt="Le choeur" loading="lazy"><p class="cf-gal-caption">Le chœur Children s Fruit</p></div>
</div>

<h2 style="font-size:1.4rem;font-weight:800;color:#1a1a2e;margin-top:3rem;margin-bottom:1rem;">Les piliers de Children’s Fruit</h2>

<div class="cf-person"><div class="cf-person-icon">A</div><div><strong>Papa ALEX</strong> — Président de Children’s Fruit</div></div>
<div class="cf-person"><div class="cf-person-icon">R</div><div><strong>Papa RANCY KAIZER</strong> — Fondateur de Children’s Fruit</div></div>
<div class="cf-person"><div class="cf-person-icon">Au</div><div><strong>Papa AUGUSTIN</strong> — Directeur d’évangélisation</div></div>
<div class="cf-person"><div class="cf-person-icon">K</div><div><strong>Frère KINGSLEY</strong> — Chef du département de production &amp; photographe</div></div>

<h2 style="font-size:1.4rem;font-weight:800;color:#1a1a2e;margin-top:3rem;">En conclusion</h2>
<p>Le Concert Children’s Fruit du 4 août 2019 restera gravé dans les mémoires. En choisissant le thème <strong>« Choisi la Vie »</strong> tiré de Deutéronome 30:18-20, le groupe a offert bien plus qu’un spectacle : un appel à la vie, à la foi, et à la décision de suivre Dieu.</p>

<div style="margin-top:2.5rem;padding:1.25rem;background:#1a1a2e;border-radius:14px;text-align:center;">
  <p style="color:rgba(255,255,255,.7);margin:0;font-size:.9rem;letter-spacing:.3px;">
    Children’s Fruit · <em>Porte ta croix et suis moi</em> · Concert 2019 — <strong style="color:#F7941D;">« Choisi la Vie »</strong>
  </p>
</div>""",
        "is_published": True,
    },
]


class Command(BaseCommand):
    help = "Charge les articles de blog initiaux dans la base de données"

    def handle(self, *args, **options):
        User = get_user_model()
        from core.models import BlogPost

        author = User.objects.filter(is_superuser=True).first()
        if not author:
            author = User.objects.first()
        if not author:
            self.stdout.write(self.style.ERROR(
                "Aucun utilisateur trouvé. Créez d'abord un superuser avec : "
                "python manage.py createsuperuser"
            ))
            return

        created = skipped = updated = 0
        for data in ARTICLES:
            existing = BlogPost.objects.filter(slug=data["slug"]).first()

            if existing:
                # Toujours mettre à jour le contenu si vide
                changed = False
                if not existing.content or len(existing.content) < 100:
                    existing.content = data["content"]
                    existing.excerpt = data["excerpt"]
                    existing.is_published = data["is_published"]
                    existing.save(update_fields=['content', 'excerpt', 'is_published'])
                    changed = True

                # Force re-upload si le thumbnail n'est pas sur Cloudinary
                needs_thumb = True
                if existing.thumbnail:
                    try:
                        url = existing.thumbnail.url
                        if 'cloudinary.com' in url or url.startswith('http'):
                            needs_thumb = False
                    except Exception:
                        pass
                if needs_thumb:
                    existing.thumbnail = None
                    existing.save(update_fields=['thumbnail'])
                    try:
                        self._attach_thumbnail(existing, data.get("thumbnail_static"), self.stdout)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'       Thumbnail ignoré : {e}'))
                    changed = True

                if changed:
                    updated += 1
                    self.stdout.write(f'  [UPD]  {data["title"][:60]}')
                else:
                    self.stdout.write(f'  [SKIP] {data["title"][:60]}')
                    skipped += 1
                continue

            post = BlogPost.objects.create(
                title=data["title"],
                slug=data["slug"],
                author=author,
                category=data["category"],
                excerpt=data["excerpt"],
                content=data["content"],
                is_published=data["is_published"],
            )
            try:
                self._attach_thumbnail(post, data.get("thumbnail_static"), self.stdout)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'       Thumbnail ignoré : {e}'))
            self.stdout.write(self.style.SUCCESS(f'  [OK]   {data["title"][:60]}'))
            created += 1

        self.stdout.write(f'\nTerminé — {created} créé(s), {updated} mis à jour, {skipped} ignoré(s).')

    def _attach_thumbnail(self, post, static_path, stdout):
        if not static_path:
            return
        # Cherche dans staticfiles/ puis static/
        for base in ['staticfiles', 'static']:
            full_path = os.path.join(settings.BASE_DIR, base, static_path)
            if os.path.exists(full_path):
                filename = os.path.basename(full_path)
                with open(full_path, 'rb') as f:
                    post.thumbnail.save(filename, File(f), save=True)
                stdout.write(f'       Thumbnail : {filename}')
                return
        stdout.write(f'       Thumbnail introuvable : {static_path}')
