import json
import secrets
import urllib.parse
import urllib.request
import urllib.error

from django.conf import settings as django_settings
from django.contrib.auth import login, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import ListView, DetailView, TemplateView, View

from .models import (
    VideoContent, KPI, Testimonial, VolunteerTask,
    FundingProject, PartnershipRequest, Casting, ActivityReport,
    VideoComment, VideoLike, CommunityMessage, DonationRecord,
    PhoneVerificationCode, BlogPost,
    LiveStream, EmissionSlot,
)
from .forms import (
    PartnershipRequestForm, VolunteerApplicationForm,
    CustomUserCreationForm, DonationForm,
    PhoneLoginForm, PhoneCodeForm,
)
from .sms import generate_otp, send_sms

_DEFAULT_KPIS = [
    {'label': 'Membres Actifs', 'value': 5000, 'icon': 'fas fa-users'},
    {'label': 'Vidéos Publiées', 'value': 200, 'icon': 'fas fa-film'},
    {'label': 'Partenaires', 'value': 50, 'icon': 'fas fa-handshake'},
    {'label': 'Vies Touchées', 'value': 10000, 'icon': 'fas fa-heart'},
]


# ─────────────────────────────────────────────────────────────
# Middleware-style last_seen update via mixin
# ─────────────────────────────────────────────────────────────
class UpdateLastSeenMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            request.user.last_seen = timezone.now()
            request.user.save(update_fields=['last_seen'])
        return super().dispatch(request, *args, **kwargs)


# ─────────────────────────────────────────────────────────────
# Public pages
# ─────────────────────────────────────────────────────────────

class HomeView(UpdateLastSeenMixin, TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Hero carousel : vidéos en vedette d'abord, complété par les plus récentes
        hero_qs = list(VideoContent.objects.filter(is_featured=True).order_by('-created_at')[:8])
        if len(hero_qs) < 5:
            ids = [v.pk for v in hero_qs]
            hero_qs += list(
                VideoContent.objects.exclude(pk__in=ids).order_by('-created_at')[: 8 - len(hero_qs)]
            )
        context['hero_videos'] = hero_qs

        # Section Web TV : vedettes sinon les plus récentes
        featured = VideoContent.objects.filter(is_featured=True).order_by('-created_at')[:6]
        context['featured_videos'] = featured if featured.exists() else VideoContent.objects.order_by('-created_at')[:6]

        # Compteurs réels pour les stats
        context['video_count'] = VideoContent.objects.count()
        context['member_count'] = get_user_model().objects.filter(is_active=True).count()

        context['recent_videos'] = VideoContent.objects.order_by('-created_at')[:3]
        context['kpis'] = KPI.objects.all()
        context['default_kpis'] = _DEFAULT_KPIS
        context['testimonials'] = Testimonial.objects.filter(is_approved=True)
        context['categories'] = VideoContent.CATEGORY_CHOICES
        context['funding_projects'] = FundingProject.objects.filter(is_active=True)[:3]
        context['blog_posts'] = BlogPost.objects.filter(is_published=True).select_related('author')[:6]
        context['blog_categories'] = BlogPost.CATEGORY_CHOICES
        return context


class DonationPageView(UpdateLastSeenMixin, View):
    template_name = 'core/donation.html'

    def get(self, request):
        form = DonationForm()
        total_raised = sum(
            d.amount for d in DonationRecord.objects.filter(confirmed=True)
        )
        return render(request, self.template_name, {
            'form': form,
            'total_raised': total_raised,
            'funding_projects': FundingProject.objects.filter(is_active=True),
        })

    def post(self, request):
        form = DonationForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            if request.user.is_authenticated:
                record.name = record.name or request.user.get_full_name() or request.user.username
                record.email = record.email or request.user.email
            record.save()
            messages.success(
                request,
                "Merci pour votre intention de don ! Veuillez effectuer le virement "
                "et envoyer une capture d'écran via la page contact."
            )
            return redirect('donation')
        total_raised = sum(
            d.amount for d in DonationRecord.objects.filter(confirmed=True)
        )
        return render(request, self.template_name, {
            'form': form,
            'total_raised': total_raised,
            'funding_projects': FundingProject.objects.filter(is_active=True),
        })


class BibleView(LoginRequiredMixin, UpdateLastSeenMixin, TemplateView):
    template_name = 'core/bible.html'
    login_url = '/accounts/login/'


class CommunityView(LoginRequiredMixin, UpdateLastSeenMixin, TemplateView):
    template_name = 'core/community.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cutoff = timezone.now() - timezone.timedelta(minutes=5)
        context['online_users'] = User.objects.filter(last_seen__gte=cutoff).exclude(pk=self.request.user.pk)
        context['recent_messages'] = CommunityMessage.objects.select_related('user').order_by('-created_at')[:50]
        context['open_tasks'] = VolunteerTask.objects.filter(status='open').order_by('deadline')[:10]
        context['castings'] = Casting.objects.filter(is_open=True).order_by('deadline')[:5]
        if self.request.user.role in ('partner', 'volunteer'):
            context['activity_reports'] = ActivityReport.objects.order_by('-created_at')[:10]
        return context


class CommunityMessageView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def get(self, request):
        after = request.GET.get('after')
        qs = CommunityMessage.objects.select_related('user').order_by('created_at')
        if after and after.isdigit():
            qs = qs.filter(id__gt=int(after))
        msgs = [
            {
                'id': m.id,
                'user': m.user.username,
                'display_name': m.user.display_name,
                'country': m.user.country,
                'role': m.user.get_role_display(),
                'text': m.text,
                'created_at': m.created_at.strftime('%H:%M'),
            }
            for m in qs[:100]
        ]
        return JsonResponse({'messages': msgs})

    def post(self, request):
        text = request.POST.get('text', '').strip()
        if not text:
            return JsonResponse({'error': 'Message vide'}, status=400)
        if len(text) > 2000:
            return JsonResponse({'error': 'Message trop long'}, status=400)
        request.user.last_seen = timezone.now()
        request.user.save(update_fields=['last_seen'])
        msg = CommunityMessage.objects.create(user=request.user, text=text)
        return JsonResponse({
            'id': msg.id,
            'user': msg.user.username,
            'display_name': msg.user.display_name,
            'country': msg.user.country,
            'role': msg.user.get_role_display(),
            'text': msg.text,
            'created_at': msg.created_at.strftime('%H:%M'),
        })


# ─────────────────────────────────────────────────────────────
# WebTV
# ─────────────────────────────────────────────────────────────

class VideoListView(LoginRequiredMixin, UpdateLastSeenMixin, ListView):
    model = VideoContent
    template_name = 'core/video_list.html'
    context_object_name = 'videos'
    paginate_by = 12
    login_url = '/accounts/login/'

    def get_queryset(self):
        qs = VideoContent.objects.all()
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category=category)
        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(title__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = VideoContent.CATEGORY_CHOICES
        context['current_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('q', '')
        return context


class VideoDetailView(LoginRequiredMixin, UpdateLastSeenMixin, DetailView):
    model = VideoContent
    template_name = 'core/video_detail.html'
    context_object_name = 'video'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video = self.get_object()
        context['related_videos'] = (
            VideoContent.objects.filter(category=video.category)
            .exclude(pk=video.pk)[:4]
        )
        # Grouper toutes les vidéos par catégorie pour la sidebar
        all_vids = VideoContent.objects.all()
        videos_by_category = []
        for cat_key, cat_label in VideoContent.CATEGORY_CHOICES:
            vids = [v for v in all_vids if v.category == cat_key]
            if vids:
                videos_by_category.append((cat_label, vids))
        context['videos_by_category'] = videos_by_category
        context['all_videos'] = all_vids
        context['user_liked'] = (
            self.request.user.is_authenticated
            and VideoLike.objects.filter(video=video, user=self.request.user).exists()
        )
        return context


class VideoCommentView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def get(self, request, pk):
        try:
            video = VideoContent.objects.get(pk=pk)
        except VideoContent.DoesNotExist:
            return JsonResponse({'comments': []})
        after = request.GET.get('after')
        qs = video.comments.select_related('user').order_by('created_at')
        if after and after.isdigit():
            qs = qs.filter(id__gt=int(after))
        return JsonResponse({'comments': [
            {
                'id': c.id,
                'user': c.user.username,
                'text': c.text,
                'created_at': c.created_at.strftime('%d/%m/%Y à %H:%M'),
            }
            for c in qs
        ]})

    def post(self, request, pk):
        try:
            video = VideoContent.objects.get(pk=pk)
        except VideoContent.DoesNotExist:
            return JsonResponse({'error': 'Vidéo introuvable'}, status=404)
        text = request.POST.get('text', '').strip()
        if not text:
            return JsonResponse({'error': 'Commentaire vide'}, status=400)
        if len(text) > 1000:
            return JsonResponse({'error': 'Trop long (max 1000 car.)'}, status=400)
        comment = VideoComment.objects.create(video=video, user=request.user, text=text)
        return JsonResponse({
            'id': comment.id,
            'user': comment.user.username,
            'text': comment.text,
            'created_at': comment.created_at.strftime('%d/%m/%Y à %H:%M'),
        })


class VideoLikeView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def post(self, request, pk):
        try:
            video = VideoContent.objects.get(pk=pk)
        except VideoContent.DoesNotExist:
            return JsonResponse({'error': 'Vidéo introuvable'}, status=404)
        like, created = VideoLike.objects.get_or_create(video=video, user=request.user)
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
        return JsonResponse({'liked': liked, 'count': video.likes.count()})


# ─────────────────────────────────────────────────────────────
# Dashboards
# ─────────────────────────────────────────────────────────────

class DashboardRedirectView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def get(self, request):
        role_map = {
            'partner':   'partner_dashboard',
            'volunteer': 'volunteer_dashboard',
            'member':    'visitor_dashboard',
            'visitor':   'visitor_dashboard',
        }
        return redirect(role_map.get(request.user.role, 'visitor_dashboard'))


class PartnerDashboardView(LoginRequiredMixin, UpdateLastSeenMixin, TemplateView):
    template_name = 'core/dashboards/partner.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'partner':
            messages.error(request, "Accès réservé aux Partenaires.")
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_videos'] = VideoContent.objects.order_by('-created_at')[:6]
        context['funding_projects'] = FundingProject.objects.filter(is_active=True)
        context['activity_reports'] = ActivityReport.objects.order_by('-created_at')[:10]
        context['community_messages'] = CommunityMessage.objects.select_related('user').order_by('-created_at')[:5]
        context['open_tasks'] = VolunteerTask.objects.filter(status='open')[:5]
        return context


class VisitorDashboardView(LoginRequiredMixin, UpdateLastSeenMixin, TemplateView):
    template_name = 'core/dashboards/visitor.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['videos'] = VideoContent.objects.all()[:8]
        context['open_tasks'] = VolunteerTask.objects.filter(status='open')
        context['castings'] = Casting.objects.filter(is_open=True)
        context['funding_projects'] = FundingProject.objects.filter(is_active=True)[:3]
        return context


class VolunteerDashboardView(LoginRequiredMixin, UpdateLastSeenMixin, TemplateView):
    template_name = 'core/dashboards/volunteer.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in ('volunteer', 'partner'):
            messages.error(request, "Accès réservé aux Bénévoles.")
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['videos'] = VideoContent.objects.all()[:6]
        context['my_tasks'] = VolunteerTask.objects.filter(assigned_to=self.request.user)
        context['open_tasks'] = VolunteerTask.objects.filter(status='open')
        context['castings'] = Casting.objects.filter(is_open=True)
        context['activity_reports'] = ActivityReport.objects.order_by('-created_at')[:5]
        context['application_form'] = VolunteerApplicationForm()
        return context


# ─────────────────────────────────────────────────────────────
# Auth / Contact
# ─────────────────────────────────────────────────────────────

class PartnershipRequestView(View):
    template_name = 'core/partnership_request.html'

    def get(self, request):
        return render(request, self.template_name, {'form': PartnershipRequestForm()})

    def post(self, request):
        form = PartnershipRequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.is_authenticated:
                obj.user = request.user
            obj.save()
            messages.success(request, "Votre demande de partenariat a été envoyée avec succès !")
            return redirect('home')
        return render(request, self.template_name, {'form': form})


class RegisterView(View):
    template_name = 'registration/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, self.template_name, {'form': CustomUserCreationForm()})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.info(
                request,
                "Compte créé ! Votre demande est en attente d'approbation par l'administrateur. "
                "Vous recevrez une confirmation dès l'activation de votre compte."
            )
            return redirect('pending_approval')
        return render(request, self.template_name, {'form': form})


# ─────────────────────────────────────────────────────────────
# Auth améliorée : Login avec vérification approbation
# ─────────────────────────────────────────────────────────────

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_superuser and not user.is_approved:
            messages.warning(
                self.request,
                "Votre compte est en attente d'approbation par l'administrateur."
            )
            return redirect('pending_approval')
        return super().form_valid(form)


class PendingApprovalView(TemplateView):
    template_name = 'registration/pending_approval.html'


# ─────────────────────────────────────────────────────────────
# Google OAuth 2.0 (sans bibliothèque tierce)
# ─────────────────────────────────────────────────────────────

_GOOGLE_AUTH_URL  = 'https://accounts.google.com/o/oauth2/v2/auth'
_GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
_GOOGLE_INFO_URL  = 'https://www.googleapis.com/oauth2/v2/userinfo'


class GoogleLoginView(View):
    def get(self, request):
        if not django_settings.GOOGLE_CLIENT_ID:
            messages.error(request, "La connexion Google n'est pas encore configurée.")
            return redirect('login')
        state = secrets.token_urlsafe(16)
        request.session['google_oauth_state'] = state
        params = {
            'client_id': django_settings.GOOGLE_CLIENT_ID,
            'redirect_uri': django_settings.GOOGLE_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'state': state,
            'prompt': 'select_account',
        }
        return redirect(_GOOGLE_AUTH_URL + '?' + urllib.parse.urlencode(params))


class GoogleCallbackView(View):
    def get(self, request):
        error = request.GET.get('error')
        if error:
            messages.error(request, "Connexion Google annulée.")
            return redirect('login')

        state = request.GET.get('state')
        if state != request.session.pop('google_oauth_state', None):
            messages.error(request, "Erreur de sécurité OAuth. Réessayez.")
            return redirect('login')

        code = request.GET.get('code')
        if not code:
            messages.error(request, "Code d'autorisation Google manquant.")
            return redirect('login')

        # Échange code → access_token
        try:
            token_data = urllib.parse.urlencode({
                'code': code,
                'client_id': django_settings.GOOGLE_CLIENT_ID,
                'client_secret': django_settings.GOOGLE_CLIENT_SECRET,
                'redirect_uri': django_settings.GOOGLE_REDIRECT_URI,
                'grant_type': 'authorization_code',
            }).encode()
            req = urllib.request.Request(_GOOGLE_TOKEN_URL, data=token_data, method='POST')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            with urllib.request.urlopen(req, timeout=10) as r:
                token_resp = json.loads(r.read())
            access_token = token_resp['access_token']

            # Récupère le profil Google
            req2 = urllib.request.Request(
                _GOOGLE_INFO_URL,
                headers={'Authorization': f'Bearer {access_token}'}
            )
            with urllib.request.urlopen(req2, timeout=10) as r:
                info = json.loads(r.read())
        except Exception:
            messages.error(request, "Impossible de communiquer avec Google. Réessayez.")
            return redirect('login')

        email = info.get('email', '').lower()
        google_id = info.get('id', '')
        if not email:
            messages.error(request, "Aucun email Google retourné.")
            return redirect('login')

        User = get_user_model()

        # Cherche le compte existant par google_id ou email
        user = (
            User.objects.filter(google_id=google_id).first()
            or User.objects.filter(email=email).first()
        )

        if user:
            if not user.google_id:
                user.google_id = google_id
                user.save(update_fields=['google_id'])
        else:
            # Crée le compte (en attente d'approbation)
            base_username = email.split('@')[0]
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{suffix}"
                suffix += 1
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=info.get('given_name', ''),
                last_name=info.get('family_name', ''),
                google_id=google_id,
                is_approved=False,
            )
            messages.info(
                request,
                "Compte Google créé ! Votre accès est en attente d'approbation par l'administrateur."
            )
            return redirect('pending_approval')

        if not user.is_superuser and not user.is_approved:
            messages.warning(request, "Votre compte est en attente d'approbation.")
            return redirect('pending_approval')

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('dashboard_redirect')


# ─────────────────────────────────────────────────────────────
# Connexion par numéro de téléphone + OTP SMS
# ─────────────────────────────────────────────────────────────

class PhoneLoginView(View):
    template_name = 'registration/phone_login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, self.template_name, {'form': PhoneLoginForm()})

    def post(self, request):
        form = PhoneLoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        phone = form.cleaned_data['phone'].strip()
        User = get_user_model()

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            messages.error(
                request,
                "Aucun compte trouvé avec ce numéro. Inscrivez-vous d'abord."
            )
            return render(request, self.template_name, {'form': form})

        # Génère et envoie le code OTP
        code = generate_otp()
        PhoneVerificationCode.objects.create(phone=phone, code=code)
        send_sms(phone, f"Children's Fruit — votre code de connexion : {code} (valable 10 min)")

        request.session['phone_login_phone'] = phone
        messages.success(request, f"Code envoyé au {phone}. Saisissez-le ci-dessous.")
        return redirect('phone_verify')


class PhoneVerifyView(View):
    template_name = 'registration/phone_verify.html'

    def get(self, request):
        if 'phone_login_phone' not in request.session:
            return redirect('phone_login')
        return render(request, self.template_name, {
            'form': PhoneCodeForm(),
            'phone': request.session['phone_login_phone'],
        })

    def post(self, request):
        phone = request.session.get('phone_login_phone')
        if not phone:
            return redirect('phone_login')

        form = PhoneCodeForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'phone': phone})

        code = form.cleaned_data['code'].strip()
        otp = (
            PhoneVerificationCode.objects
            .filter(phone=phone, code=code, is_used=False)
            .order_by('-created_at')
            .first()
        )

        if not otp or not otp.is_valid():
            messages.error(request, "Code incorrect ou expiré. Réessayez.")
            return render(request, self.template_name, {'form': form, 'phone': phone})

        otp.is_used = True
        otp.save(update_fields=['is_used'])
        del request.session['phone_login_phone']

        User = get_user_model()
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            messages.error(request, "Compte introuvable.")
            return redirect('phone_login')

        if not user.is_superuser and not user.is_approved:
            messages.warning(request, "Votre compte est en attente d'approbation.")
            return redirect('pending_approval')

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f"Bienvenue, {user.display_name} !")
        return redirect('dashboard_redirect')


# ─────────────────────────────────────────────────────────────
# Blog
# ─────────────────────────────────────────────────────────────

class BlogListView(TemplateView):
    template_name = 'core/blog_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = BlogPost.objects.filter(is_published=True).select_related('author')
        category = self.request.GET.get('category', '')
        if category:
            qs = qs.filter(category=category)
        context['posts'] = qs
        context['blog_categories'] = BlogPost.CATEGORY_CHOICES
        context['current_category'] = category
        return context


class BlogDetailView(DetailView):
    model = BlogPost
    template_name = 'core/blog_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True).select_related('author')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        context['related_posts'] = (
            BlogPost.objects.filter(is_published=True, category=post.category)
            .exclude(pk=post.pk)[:3]
        )
        return context


# ─────────────────────────────────────────────────────────────
# Bible API proxy (avoids browser CORS restrictions)
# ─────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# LIVE STREAMING
# ──────────────────────────────────────────────────────────────────────────────

class LiveView(TemplateView):
    template_name = 'core/live.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.utils import timezone
        today = timezone.localdate()
        ctx['live']           = LiveStream.get_active()
        ctx['schedule_today'] = EmissionSlot.objects.filter(date=today)
        ctx['schedule_week']  = (EmissionSlot.objects
                                  .filter(date__gte=today)
                                  .exclude(date=today)
                                  .order_by('date', 'start_time')[:30])
        return ctx


class LiveStatusAPIView(View):
    def get(self, request):
        live = LiveStream.get_active()
        if live:
            return JsonResponse({
                'is_live':    True,
                'title':      live.title,
                'platform':   live.platform,
                'embed_url':  live.get_embed_url(),
            })
        return JsonResponse({'is_live': False})


class LiveControlView(LoginRequiredMixin, View):
    login_url    = '/accounts/login/'
    template_name = 'core/live_control.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('Accès réservé au staff.')
        return super().dispatch(request, *args, **kwargs)

    def _get_or_create_stream(self):
        live, _ = LiveStream.objects.get_or_create(
            pk=1,
            defaults={'title': "Children's Fruit Live", 'platform': 'youtube'},
        )
        return live

    def get(self, request):
        from django.utils import timezone
        today = timezone.localdate()
        live  = self._get_or_create_stream()
        return render(request, self.template_name, {
            'live':           live,
            'slots_today':    EmissionSlot.objects.filter(date=today),
            'today':          today,
            'category_choices': EmissionSlot.CATEGORY_CHOICES,
        })

    def post(self, request):
        from django.utils import timezone
        action = request.POST.get('action')
        live   = self._get_or_create_stream()

        if action == 'toggle_live':
            live.is_live = not live.is_live
            if live.is_live:
                live.started_at = timezone.now()
            live.save()
            state = '🔴 Direct lancé !' if live.is_live else '⚫ Direct arrêté.'
            messages.success(request, state)

        elif action == 'update_stream':
            live.title       = request.POST.get('title', live.title).strip() or live.title
            live.platform    = request.POST.get('platform', live.platform)
            live.stream_url  = request.POST.get('stream_url', '').strip()
            live.description = request.POST.get('description', '').strip()
            live.save()
            messages.success(request, 'Paramètres du direct enregistrés.')

        elif action == 'add_slot':
            try:
                EmissionSlot.objects.create(
                    title       = request.POST.get('slot_title', '').strip(),
                    date        = request.POST.get('slot_date'),
                    start_time  = request.POST.get('start_time'),
                    end_time    = request.POST.get('end_time'),
                    category    = request.POST.get('category', 'culte'),
                    presenter   = request.POST.get('presenter', '').strip(),
                    description = request.POST.get('slot_description', '').strip(),
                )
                messages.success(request, 'Créneau ajouté à la grille.')
            except Exception as exc:
                messages.error(request, f'Erreur : {exc}')

        elif action == 'delete_slot':
            EmissionSlot.objects.filter(pk=request.POST.get('slot_id')).delete()
            messages.success(request, 'Créneau supprimé.')

        return redirect('live_control')


# ──────────────────────────────────────────────────────────────────────────────
# BIBLE API PROXY
# ──────────────────────────────────────────────────────────────────────────────

_BIBLE_BASE   = 'https://bible.helloao.org/api'
_PROXY_TIMEOUT = 10

# Standard USFM book abbreviations used by bible.helloao.org (index 0 = book 1)
_BOOK_ABBR = [
    'GEN','EXO','LEV','NUM','DEU','JOS','JDG','RUT','1SA','2SA',
    '1KI','2KI','1CH','2CH','EZR','NEH','EST','JOB','PSA','PRO',
    'ECC','SNG','ISA','JER','LAM','EZK','DAN','HOS','JOL','AMO',
    'OBA','JON','MIC','NAM','HAB','ZEP','HAG','ZEC','MAL',
    'MAT','MRK','LUK','JHN','ACT','ROM','1CO','2CO','GAL','EPH',
    'PHP','COL','1TH','2TH','1TI','2TI','TIT','PHM','HEB','JAS',
    '1PE','2PE','1JN','2JN','3JN','JUD','REV',
]

# ISO 639-3 → 639-1 for the front-end language labels
_LANG_3_TO_2 = {
    'eng':'en','fra':'fr','deu':'de','spa':'es','por':'pt','ita':'it',
    'rus':'ru','ara':'ar','zho':'zh','kor':'ko','jpn':'ja','nld':'nl',
    'pol':'pl','ron':'ro','swa':'sw','hau':'ha','yor':'yo','afr':'af',
    'hin':'hi','ben':'bn','tur':'tr','vie':'vi','ind':'id','msa':'ms',
}


def _fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'ChildrensFruitApp/1.0'})
    with urllib.request.urlopen(req, timeout=_PROXY_TIMEOUT) as r:
        return json.loads(r.read().decode('utf-8'))


@method_decorator(cache_page(60 * 60 * 6), name='dispatch')  # cache 6 h
class BibleTranslationsProxyView(View):
    def get(self, request):
        try:
            data = _fetch_json(f'{_BIBLE_BASE}/available_translations.json')
            # Normalize to {ABBR: {language, translation, abbreviation}}
            result = {}
            for t in data.get('translations', []):
                abbr = t.get('id', '').upper()
                if not abbr:
                    continue
                lang3 = t.get('languageCode', '')[:3].lower()
                result[abbr] = {
                    'language':     _LANG_3_TO_2.get(lang3, lang3[:2]),
                    'translation':  t.get('name', abbr),
                    'abbreviation': abbr,
                }
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=502)


class BibleChapterProxyView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def get(self, request, translation, book_nr, chapter_nr):
        import re as _re
        translation = translation.upper()
        if not _re.match(r'^[A-Z0-9]{2,12}$', translation):
            return JsonResponse({'error': 'Invalid translation'}, status=400)
        if not (1 <= book_nr <= 66) or not (1 <= chapter_nr <= 150):
            return JsonResponse({'error': 'Invalid reference'}, status=400)

        book_abbr = _BOOK_ABBR[book_nr - 1]
        try:
            data = _fetch_json(f'{_BIBLE_BASE}/{translation}/{book_abbr}/{chapter_nr}.json')
            # Normalize to the format the front-end already expects
            verses = {}
            for v in data.get('verses', []):
                num = v.get('number') or v.get('verse', 0)
                verses[str(num)] = {'text': v.get('text', '')}
            normalized = {
                'translation': translation,
                'book_name':   data.get('book', {}).get('name', ''),
                'chapter':     chapter_nr,
                'verses':      verses,
            }
            return JsonResponse(normalized)
        except urllib.error.HTTPError as e:
            return JsonResponse({'error': f'Not found ({e.code})'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=502)
