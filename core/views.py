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
    StudyCourse, CourseResource, CourseEnrollment, ResourceProgress,
    Quiz, QuizQuestion, QuizChoice, QuizAttempt, QuizAnswer, Certificate,
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

        # Live stream actif
        context['live_stream'] = LiveStream.get_active()

        # Hero carousel : vidéos en vedette d'abord, complété par les plus récentes
        hero_qs = list(VideoContent.objects.filter(is_featured=True).order_by('-created_at')[:8])
        if len(hero_qs) < 5:
            ids = [v.pk for v in hero_qs]
            hero_qs += list(
                VideoContent.objects.exclude(pk__in=ids).order_by('-created_at')[: 8 - len(hero_qs)]
            )
        context['hero_videos'] = hero_qs

        # Section Web TV : vedettes en priorité, complété par les plus récentes jusqu'à 6
        featured = list(VideoContent.objects.filter(is_featured=True).order_by('-created_at')[:6])
        if len(featured) < 6:
            ids = [v.pk for v in featured]
            featured += list(VideoContent.objects.exclude(pk__in=ids).order_by('-created_at')[:6 - len(featured)])
        context['featured_videos'] = featured

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
        context['recent_messages'] = CommunityMessage.objects.select_related('user').order_by('-created_at')[:60]
        context['open_tasks'] = VolunteerTask.objects.filter(status='open').order_by('deadline')[:10]
        context['castings'] = Casting.objects.filter(is_open=True).order_by('deadline')[:5]
        if self.request.user.role in ('partner', 'volunteer'):
            context['activity_reports'] = ActivityReport.objects.order_by('-created_at')[:10]
        today = timezone.localdate()
        context['today'] = today
        context['today_msg_count'] = CommunityMessage.objects.filter(created_at__date=today, is_deleted=False).count()
        context['total_members'] = User.objects.filter(is_active=True).count()
        return context


def _serialize_msg(m, request):
    if m.is_deleted:
        return {'id': m.id, 'msg_type': 'deleted', 'user': m.user.username, 'created_at': m.created_at.strftime('%H:%M')}
    return {
        'id':            m.id,
        'user':          m.user.username,
        'display_name':  m.user.display_name,
        'country':       m.user.country,
        'role':          m.user.get_role_display(),
        'msg_type':      m.msg_type,
        'text':          m.text,
        'sticker_url':   m.sticker_url,
        'image_url':     request.build_absolute_uri(m.image.url) if m.image else '',
        'voice_url':     request.build_absolute_uri(m.voice_file.url) if m.voice_file else '',
        'video_file_url': request.build_absolute_uri(m.video_file.url) if m.video_file else '',
        'video_url':     m.video_url,
        'youtube_embed': m.youtube_embed_url,
        'document_url':  request.build_absolute_uri(m.document.url) if m.document else '',
        'document_name': m.document_name,
        'is_edited':     bool(m.edited_at),
        'created_at':    m.created_at.strftime('%H:%M'),
    }


class CommunityMessageView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def get(self, request):
        after = request.GET.get('after')
        qs = CommunityMessage.objects.select_related('user').order_by('created_at')
        if after and after.isdigit():
            qs = qs.filter(id__gt=int(after))
        return JsonResponse({'messages': [_serialize_msg(m, request) for m in qs[:100]]})

    def post(self, request):
        msg_type = request.POST.get('msg_type', 'text')
        request.user.last_seen = timezone.now()
        request.user.save(update_fields=['last_seen'])

        if msg_type == 'image':
            img = request.FILES.get('image')
            if not img:
                return JsonResponse({'error': 'Aucune image'}, status=400)
            if img.size > 8 * 1024 * 1024:
                return JsonResponse({'error': 'Image trop grande (max 8 Mo)'}, status=400)
            msg = CommunityMessage.objects.create(user=request.user, msg_type='image', image=img)

        elif msg_type == 'sticker':
            sticker_url = request.POST.get('sticker_url', '').strip()
            if not sticker_url:
                return JsonResponse({'error': 'Sticker invalide'}, status=400)
            msg = CommunityMessage.objects.create(user=request.user, msg_type='sticker', sticker_url=sticker_url)

        elif msg_type == 'voice':
            voice = request.FILES.get('voice')
            if not voice:
                return JsonResponse({'error': 'Aucun fichier vocal'}, status=400)
            if voice.size > 10 * 1024 * 1024:
                return JsonResponse({'error': 'Fichier trop grand (max 10 Mo)'}, status=400)
            msg = CommunityMessage.objects.create(user=request.user, msg_type='voice', voice_file=voice)

        elif msg_type == 'video':
            video_url  = request.POST.get('video_url', '').strip()
            video_file = request.FILES.get('video_file')
            if not video_url and not video_file:
                return JsonResponse({'error': 'Aucune vidéo fournie'}, status=400)
            if video_file and video_file.size > 100 * 1024 * 1024:
                return JsonResponse({'error': 'Vidéo trop grande (max 100 Mo)'}, status=400)
            kw = {'msg_type': 'video'}
            if video_url:  kw['video_url']  = video_url
            if video_file: kw['video_file'] = video_file
            msg = CommunityMessage.objects.create(user=request.user, **kw)

        elif msg_type == 'document':
            doc = request.FILES.get('document')
            if not doc:
                return JsonResponse({'error': 'Aucun document'}, status=400)
            if doc.size > 15 * 1024 * 1024:
                return JsonResponse({'error': 'Document trop grand (max 15 Mo)'}, status=400)
            msg = CommunityMessage.objects.create(
                user=request.user, msg_type='document', document=doc, document_name=doc.name)

        else:
            text = request.POST.get('text', '').strip()
            if not text:
                return JsonResponse({'error': 'Message vide'}, status=400)
            if len(text) > 2000:
                return JsonResponse({'error': 'Message trop long'}, status=400)
            msg = CommunityMessage.objects.create(user=request.user, msg_type='text', text=text)

        return JsonResponse(_serialize_msg(msg, request))


class CommunityMessageDetailView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def _get(self, pk, user):
        try:
            msg = CommunityMessage.objects.get(pk=pk)
        except CommunityMessage.DoesNotExist:
            return None, JsonResponse({'error': 'Message introuvable'}, status=404)
        if msg.user != user and not user.is_staff:
            return None, JsonResponse({'error': 'Non autorisé'}, status=403)
        return msg, None

    def patch(self, request, pk):
        import json as _json
        msg, err = self._get(pk, request.user)
        if err:
            return err
        if msg.is_deleted:
            return JsonResponse({'error': 'Message supprimé'}, status=400)
        if msg.msg_type != 'text':
            return JsonResponse({'error': 'Seuls les textes sont modifiables'}, status=400)
        try:
            data = _json.loads(request.body)
        except Exception:
            return JsonResponse({'error': 'Corps invalide'}, status=400)
        text = data.get('text', '').strip()
        if not text:
            return JsonResponse({'error': 'Message vide'}, status=400)
        if len(text) > 2000:
            return JsonResponse({'error': 'Trop long'}, status=400)
        msg.text = text
        msg.edited_at = timezone.now()
        msg.save(update_fields=['text', 'edited_at'])
        return JsonResponse({'ok': True, 'text': msg.text})

    def delete(self, request, pk):
        msg, err = self._get(pk, request.user)
        if err:
            return err
        if not msg.is_deleted:
            msg.is_deleted = True
            msg.save(update_fields=['is_deleted'])
        return JsonResponse({'ok': True})


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
        from datetime import time as dt_time

        now_local = timezone.localtime()
        today     = now_local.date()

        ctx['live']      = LiveStream.get_active()
        ctx['now_hour']  = now_local.hour
        ctx['now_min']   = now_local.minute
        ctx['today']     = today

        today_slots = list(EmissionSlot.objects.filter(date=today).order_by('start_time'))

        # Grille 24h : chaque slot apparaît dans toutes les heures qu'il couvre
        grid = []
        for h in range(24):
            active = []
            for s in today_slots:
                sh = s.start_time.hour
                eh = s.end_time.hour
                # Slot couvre cette heure si :
                # - il commence à cette heure
                # - ou il commence avant et se termine après (ou à minuit = 0 = fin de journée)
                if sh == h:
                    active.append(s)
                elif sh < h:
                    if eh == 0 or eh > h:   # se termine après h, ou minuit (couvre jusqu'à fin)
                        active.append(s)
            grid.append({'hour': h, 'slots': active, 'is_now': now_local.hour == h})

        ctx['grid_24h'] = grid

        ctx['schedule_week'] = (EmissionSlot.objects
                                .filter(date__gt=today)
                                .order_by('date', 'start_time')[:40])

        u = self.request.user
        ctx['can_manage_live'] = u.is_authenticated and (
            u.is_staff or u.has_perm('core.can_manage_live')
        )
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
# BIBLE API PROXY  (bolls.life — gratuit, fiable, LSG français inclus)
# Clé BIBLE_API_KEY conservée dans .env pour API future si besoin
# ──────────────────────────────────────────────────────────────────────────────

_BOLLS_BASE    = 'https://bolls.life'
_PROXY_TIMEOUT = 12

# Noms français des 66 livres (index 1-66)
_FR_BOOK_NAMES = {
     1:'Genèse', 2:'Exode', 3:'Lévitique', 4:'Nombres', 5:'Deutéronome',
     6:'Josué', 7:'Juges', 8:'Ruth', 9:'1 Samuel', 10:'2 Samuel',
    11:'1 Rois', 12:'2 Rois', 13:'1 Chroniques', 14:'2 Chroniques',
    15:'Esdras', 16:'Néhémie', 17:'Esther', 18:'Job', 19:'Psaumes',
    20:'Proverbes', 21:'Ecclésiaste', 22:'Cantique des Cantiques',
    23:'Ésaïe', 24:'Jérémie', 25:'Lamentations', 26:'Ézéchiel',
    27:'Daniel', 28:'Osée', 29:'Joël', 30:'Amos', 31:'Abdias',
    32:'Jonas', 33:'Michée', 34:'Nahum', 35:'Habacuc', 36:'Sophonie',
    37:'Aggée', 38:'Zacharie', 39:'Malachie', 40:'Matthieu', 41:'Marc',
    42:'Luc', 43:'Jean', 44:'Actes', 45:'Romains', 46:'1 Corinthiens',
    47:'2 Corinthiens', 48:'Galates', 49:'Éphésiens', 50:'Philippiens',
    51:'Colossiens', 52:'1 Thessaloniciens', 53:'2 Thessaloniciens',
    54:'1 Timothée', 55:'2 Timothée', 56:'Tite', 57:'Philémon',
    58:'Hébreux', 59:'Jacques', 60:'1 Pierre', 61:'2 Pierre',
    62:'1 Jean', 63:'2 Jean', 64:'3 Jean', 65:'Jude', 66:'Apocalypse',
}

# Langue native → code ISO 639-1
_LANG_NAME_TO_2 = {
    'french':'fr', 'english':'en', 'spanish':'es', 'portuguese':'pt',
    'german':'de', 'italian':'it', 'russian':'ru', 'arabic':'ar',
    'chinese':'zh', 'korean':'ko', 'japanese':'ja', 'dutch':'nl',
    'polish':'pl', 'romanian':'ro', 'swahili':'sw', 'hausa':'ha',
    'yoruba':'yo', 'afrikaans':'af', 'hindi':'hi', 'turkish':'tr',
    'indonesian':'id', 'malay':'ms', 'vietnamese':'vi',
    # also accept native names
    'français':'fr', 'español':'es', 'português':'pt',
    'deutsch':'de', 'italiano':'it',
}


def _fetch_json(url, headers=None):
    h = {'User-Agent': 'ChildrensFruitApp/1.0'}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=_PROXY_TIMEOUT) as r:
        return json.loads(r.read().decode('utf-8'))


@method_decorator(cache_page(60 * 60 * 12), name='dispatch')  # cache 12 h
class BibleTranslationsProxyView(View):
    def get(self, request):
        try:
            data = _fetch_json(f'{_BOLLS_BASE}/get-translations/')
            result = {}
            for t in data:
                abbr = (t.get('short_name') or '').strip()
                if not abbr:
                    continue
                lang_raw = (t.get('language') or '').lower().strip()
                lang2 = _LANG_NAME_TO_2.get(lang_raw, lang_raw[:2] if len(lang_raw) >= 2 else 'xx')
                result[abbr] = {
                    'language':     lang2,
                    'translation':  t.get('name', abbr),
                    'abbreviation': abbr,
                    'books':        t.get('books_number', 66),
                }
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=502)


class BibleChapterProxyView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def get(self, request, translation, book_nr, chapter_nr):
        import re as _re
        translation = translation.upper()
        if not _re.match(r'^[A-Z0-9]{2,15}$', translation):
            return JsonResponse({'error': 'Invalid translation'}, status=400)
        if not (1 <= book_nr <= 66) or not (1 <= chapter_nr <= 150):
            return JsonResponse({'error': 'Invalid reference'}, status=400)

        try:
            # bolls.life takes book number directly (1-66) — no abbreviation lookup needed
            data = _fetch_json(f'{_BOLLS_BASE}/get-chapter/{translation}/{book_nr}/{chapter_nr}/')
            verses = {}
            for v in data:
                num = str(v.get('verse') or v.get('number') or 0)
                text = (v.get('text') or '').strip()
                if num and num != '0' and text:
                    verses[num] = {'text': text}
            return JsonResponse({
                'translation': translation,
                'book_name':   _FR_BOOK_NAMES.get(book_nr, ''),
                'chapter':     chapter_nr,
                'verses':      verses,
            })
        except urllib.error.HTTPError as e:
            return JsonResponse({'error': f'Passage introuvable ({e.code})'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=502)


# ──────────────────────────────────────────────────────────────────────────────
# BIBLIOTHÈQUE D'ÉTUDE
# ──────────────────────────────────────────────────────────────────────────────

class StudyLibraryView(LoginRequiredMixin, UpdateLastSeenMixin, TemplateView):
    login_url = '/accounts/login/'
    template_name = 'core/study_library.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        courses = StudyCourse.objects.filter(is_published=True).prefetch_related('resources')
        user = self.request.user
        enrollments = {e.course_id: e for e in CourseEnrollment.objects.filter(user=user)}
        course_list = []
        for c in courses:
            enroll = enrollments.get(c.pk)
            course_list.append({
                'course': c,
                'enrollment': enroll,
                'progress': enroll.progress_pct if enroll else 0,
                'has_cert': Certificate.objects.filter(user=user, course=c).exists(),
            })
        ctx['course_list'] = course_list
        return ctx


class CourseDetailView(LoginRequiredMixin, UpdateLastSeenMixin, View):
    login_url = '/accounts/login/'
    template_name = 'core/study_course.html'

    def get(self, request, pk):
        course = StudyCourse.objects.filter(pk=pk, is_published=True).prefetch_related('resources').first()
        if not course:
            from django.http import Http404
            raise Http404

        enrollment, _ = CourseEnrollment.objects.get_or_create(user=request.user, course=course)
        resources = list(course.resources.all())
        completed_ids = set(
            ResourceProgress.objects.filter(
                user=request.user, resource__in=resources, completed=True
            ).values_list('resource_id', flat=True)
        )
        resource_list = []
        for r in resources:
            has_quiz = hasattr(r, 'quiz')
            resource_list.append({
                'resource': r,
                'completed': r.pk in completed_ids,
                'has_quiz': has_quiz,
            })

        all_done = len(completed_ids) == len(resources) and len(resources) > 0
        has_exam = hasattr(course, 'final_exam')
        cert = Certificate.objects.filter(user=request.user, course=course).first()
        best_exam = None
        if has_exam:
            best_exam = (
                QuizAttempt.objects.filter(user=request.user, quiz=course.final_exam)
                .order_by('-score').first()
            )

        return render(request, self.template_name, {
            'course': course,
            'enrollment': enrollment,
            'resource_list': resource_list,
            'all_resources_done': all_done,
            'has_exam': has_exam,
            'best_exam': best_exam,
            'certificate': cert,
        })


class ResourceViewerView(LoginRequiredMixin, UpdateLastSeenMixin, View):
    login_url = '/accounts/login/'
    template_name = 'core/study_resource.html'

    def _get_objects(self, request, course_pk, pk):
        course = StudyCourse.objects.filter(pk=course_pk, is_published=True).first()
        resource = CourseResource.objects.filter(pk=pk, course=course).first() if course else None
        if not course or not resource:
            from django.http import Http404
            raise Http404
        enrollment, _ = CourseEnrollment.objects.get_or_create(user=request.user, course=course)
        progress, _ = ResourceProgress.objects.get_or_create(user=request.user, resource=resource)
        return course, resource, enrollment, progress

    def get(self, request, course_pk, pk):
        course, resource, enrollment, progress = self._get_objects(request, course_pk, pk)
        resources = list(course.resources.all())
        idx = next((i for i, r in enumerate(resources) if r.pk == resource.pk), 0)
        prev_resource = resources[idx - 1] if idx > 0 else None
        next_resource = resources[idx + 1] if idx < len(resources) - 1 else None
        has_quiz = hasattr(resource, 'quiz')
        return render(request, self.template_name, {
            'course': course,
            'resource': resource,
            'progress': progress,
            'prev_resource': prev_resource,
            'next_resource': next_resource,
            'has_quiz': has_quiz,
            'is_youtube': resource.is_youtube_video(),
            'embed_url': resource.get_embed_url() if resource.resource_type == 'video' else '',
        })

    def post(self, request, course_pk, pk):
        course, resource, enrollment, progress = self._get_objects(request, course_pk, pk)
        if not progress.completed:
            progress.completed = True
            progress.completed_at = timezone.now()
            progress.save()
            total = course.resources.count()
            done = ResourceProgress.objects.filter(
                user=request.user, resource__course=course, completed=True
            ).count()
            if total > 0 and done >= total and not enrollment.completed_at:
                enrollment.completed_at = timezone.now()
                enrollment.save()
        if hasattr(resource, 'quiz'):
            return redirect('study_quiz', course_pk=course_pk, pk=pk)
        return redirect('study_course', pk=course_pk)


class QuizView(LoginRequiredMixin, UpdateLastSeenMixin, View):
    login_url = '/accounts/login/'
    template_name = 'core/study_quiz.html'

    def _get_objects(self, request, course_pk, pk):
        course = StudyCourse.objects.filter(pk=course_pk, is_published=True).first()
        resource = CourseResource.objects.filter(pk=pk, course=course).select_related('quiz').first() if course else None
        if not course or not resource or not hasattr(resource, 'quiz'):
            from django.http import Http404
            raise Http404
        CourseEnrollment.objects.get_or_create(user=request.user, course=course)
        return course, resource, resource.quiz

    def get(self, request, course_pk, pk):
        course, resource, quiz = self._get_objects(request, course_pk, pk)
        questions = quiz.questions.prefetch_related('choices').all()
        best = QuizAttempt.objects.filter(user=request.user, quiz=quiz).order_by('-score').first()
        return render(request, self.template_name, {
            'course': course,
            'resource': resource,
            'quiz': quiz,
            'questions': questions,
            'best_attempt': best,
        })

    def post(self, request, course_pk, pk):
        course, resource, quiz = self._get_objects(request, course_pk, pk)
        questions = list(quiz.questions.prefetch_related('choices').all())
        attempt = QuizAttempt.objects.create(user=request.user, quiz=quiz)
        for q in questions:
            choice_id = request.POST.get(f'q_{q.pk}')
            choice = None
            if choice_id:
                try:
                    choice = QuizChoice.objects.get(pk=int(choice_id), question=q)
                except (QuizChoice.DoesNotExist, ValueError):
                    pass
            QuizAnswer.objects.create(attempt=attempt, question=q, selected_choice=choice)
        attempt.calculate_score()
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=['score', 'passed', 'completed_at'])
        if attempt.passed:
            progress, _ = ResourceProgress.objects.get_or_create(user=request.user, resource=resource)
            if not progress.completed:
                progress.completed = True
                progress.completed_at = timezone.now()
                progress.save(update_fields=['completed', 'completed_at'])
        return redirect('study_quiz_result', course_pk=course_pk, pk=pk, attempt_pk=attempt.pk)


class QuizResultView(LoginRequiredMixin, UpdateLastSeenMixin, View):
    login_url = '/accounts/login/'
    template_name = 'core/study_quiz_result.html'

    def get(self, request, course_pk, pk, attempt_pk):
        from django.shortcuts import get_object_or_404
        course = get_object_or_404(StudyCourse, pk=course_pk, is_published=True)
        resource = get_object_or_404(CourseResource, pk=pk, course=course)
        attempt = get_object_or_404(QuizAttempt, pk=attempt_pk, user=request.user, quiz=resource.quiz)
        answers = attempt.answers.select_related('question', 'selected_choice').prefetch_related('question__choices').all()
        return render(request, self.template_name, {
            'course': course,
            'resource': resource,
            'attempt': attempt,
            'answers': answers,
        })


class FinalExamView(LoginRequiredMixin, UpdateLastSeenMixin, View):
    login_url = '/accounts/login/'
    template_name = 'core/study_final_exam.html'

    def _get_objects(self, request, course_pk):
        course = StudyCourse.objects.filter(pk=course_pk, is_published=True).first()
        if not course or not hasattr(course, 'final_exam'):
            from django.http import Http404
            raise Http404
        enrollment, _ = CourseEnrollment.objects.get_or_create(user=request.user, course=course)
        return course, course.final_exam, enrollment

    def get(self, request, course_pk):
        course, exam, enrollment = self._get_objects(request, course_pk)
        total = course.resources.count()
        done = ResourceProgress.objects.filter(
            user=request.user, resource__course=course, completed=True
        ).count()
        all_done = total > 0 and done >= total
        questions = exam.questions.prefetch_related('choices').all()
        best = QuizAttempt.objects.filter(user=request.user, quiz=exam).order_by('-score').first()
        cert = Certificate.objects.filter(user=request.user, course=course).first()
        return render(request, self.template_name, {
            'course': course,
            'exam': exam,
            'questions': questions,
            'all_resources_done': all_done,
            'best_attempt': best,
            'certificate': cert,
        })

    def post(self, request, course_pk):
        course, exam, enrollment = self._get_objects(request, course_pk)

        # Guard: all resources must be completed before the exam
        total = course.resources.count()
        done = ResourceProgress.objects.filter(
            user=request.user, resource__course=course, completed=True
        ).count()
        if total > 0 and done < total:
            messages.error(request, "Vous devez d'abord terminer toutes les ressources avant de passer l'examen final.")
            return redirect('study_final_exam', course_pk=course_pk)

        questions = list(exam.questions.prefetch_related('choices').all())
        attempt = QuizAttempt.objects.create(user=request.user, quiz=exam)
        for q in questions:
            choice_id = request.POST.get(f'q_{q.pk}')
            choice = None
            if choice_id:
                try:
                    choice = QuizChoice.objects.get(pk=int(choice_id), question=q)
                except (QuizChoice.DoesNotExist, ValueError):
                    pass
            QuizAnswer.objects.create(attempt=attempt, question=q, selected_choice=choice)
        attempt.calculate_score()
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=['score', 'passed', 'completed_at'])
        if attempt.passed:
            if not enrollment.completed_at:
                enrollment.completed_at = timezone.now()
                enrollment.save(update_fields=['completed_at'])
            Certificate.objects.get_or_create(
                user=request.user,
                course=course,
                defaults={'attempt': attempt},
            )
        return redirect('study_exam_result', course_pk=course_pk, attempt_pk=attempt.pk)


class ExamResultView(LoginRequiredMixin, UpdateLastSeenMixin, View):
    login_url = '/accounts/login/'
    template_name = 'core/study_exam_result.html'

    def get(self, request, course_pk, attempt_pk):
        from django.shortcuts import get_object_or_404
        course = get_object_or_404(StudyCourse, pk=course_pk, is_published=True)
        exam = getattr(course, 'final_exam', None)
        if not exam:
            from django.http import Http404
            raise Http404
        attempt = get_object_or_404(QuizAttempt, pk=attempt_pk, user=request.user, quiz=exam)
        answers = attempt.answers.select_related('question', 'selected_choice').prefetch_related('question__choices').all()
        cert = Certificate.objects.filter(user=request.user, course=course).first()
        return render(request, self.template_name, {
            'course': course,
            'attempt': attempt,
            'answers': answers,
            'certificate': cert,
        })


class CertificateView(LoginRequiredMixin, UpdateLastSeenMixin, View):
    login_url = '/accounts/login/'
    template_name = 'core/study_certificate.html'

    def get(self, request, course_pk):
        from django.shortcuts import get_object_or_404
        course = get_object_or_404(StudyCourse, pk=course_pk, is_published=True)
        cert = Certificate.objects.filter(user=request.user, course=course).first()
        if not cert:
            from django.http import Http404
            raise Http404
        return render(request, self.template_name, {
            'course': course,
            'certificate': cert,
            'user': request.user,
        })
