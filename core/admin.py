from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html, mark_safe

from .models import (
    CustomUser, VideoContent, KPI, Testimonial,
    VolunteerTask, PartnershipRequest, FundingProject,
    ActivityReport, Casting, DonationRecord,
    VideoComment, VideoLike, CommunityMessage,
    PhoneVerificationCode, BlogPost,
    LiveStream, EmissionSlot,
    StudyCourse, CourseResource, CourseEnrollment, ResourceProgress,
    Quiz, QuizQuestion, QuizChoice, QuizAttempt, QuizAnswer, Certificate,
    NewsletterSubscriber,
)


class VideoContentAdminForm(forms.ModelForm):
    class Meta:
        model = VideoContent
        fields = '__all__'
        widgets = {
            'youtube_url': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': (
                    'Exemples acceptés :\n'
                    '• https://www.youtube.com/watch?v=VIDEO_ID\n'
                    '• https://youtu.be/VIDEO_ID\n'
                    '• https://youtube.com/shorts/VIDEO_ID\n'
                    '• <iframe ... src="https://www.youtube.com/embed/VIDEO_ID" ...></iframe>\n\n'
                    'Laissez vide si vous uploadez un fichier vidéo ci-dessous.'
                ),
            }),
        }

    _YT_PATTERNS = [
        r'youtube\.com/watch\?(?:.*&)?v=([^&\s"]+)',
        r'youtu\.be/([^?\s"]+)',
        r'youtube(?:-nocookie)?\.com/embed/([^?\s"/]+)',
        r'youtube\.com/shorts/([^?\s"]+)',
    ]

    def clean(self):
        import re
        cleaned_data = super().clean()
        youtube_url = cleaned_data.get('youtube_url', '').strip()
        video_file = cleaned_data.get('video_file')

        if not youtube_url and not video_file:
            raise forms.ValidationError(
                'Fournissez soit une URL/code YouTube, soit un fichier vidéo (MP4, WebM, OGG).'
            )

        if youtube_url:
            found = any(re.search(p, youtube_url) for p in self._YT_PATTERNS)
            if not found:
                self.add_error(
                    'youtube_url',
                    'Aucun identifiant YouTube trouvé. Collez l\'URL de la vidéo '
                    '(youtube.com/watch?v=...) ou le code <iframe> fourni par YouTube → Partager → Intégrer.',
                )

        cleaned_data['youtube_url'] = youtube_url
        return cleaned_data


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'display_name_col', 'country', 'phone',
        'role', 'is_approved', 'is_active', 'date_joined',
    )
    list_filter = ('is_approved', 'role', 'is_active', 'is_staff')
    list_editable = ('is_approved',)
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    actions = ['approve_accounts', 'revoke_approval']

    fieldsets = UserAdmin.fieldsets + (
        ("Profil Children's Fruit", {
            'fields': ('role', 'country', 'phone', 'google_id', 'is_approved', 'avatar', 'bio', 'last_seen'),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profil', {'fields': ('role', 'country', 'phone', 'is_approved')}),
    )

    @admin.display(description='Nom complet')
    def display_name_col(self, obj):
        return obj.display_name

    @admin.action(description='✅ Approuver les comptes sélectionnés')
    def approve_accounts(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} compte(s) approuvé(s).")

    @admin.action(description='❌ Révoquer l\'approbation')
    def revoke_approval(self, request, queryset):
        updated = queryset.exclude(is_superuser=True).update(is_approved=False)
        self.message_user(request, f"{updated} compte(s) révoqué(s).")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display  = ('title', 'category', 'author', 'is_published', 'created_at')
    list_filter   = ('is_published', 'category')
    list_editable = ('is_published',)
    search_fields = ('title', 'content', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'author', 'category', 'is_published')}),
        ('Contenu', {'fields': ('thumbnail', 'excerpt', 'content')}),
        ('Dates', {'fields': ('created_at', 'updated_at')}),
    )
    actions = ['publish_posts', 'unpublish_posts']

    @admin.action(description='✅ Publier les articles sélectionnés')
    def publish_posts(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} article(s) publié(s).")

    @admin.action(description='⏸ Dépublier les articles sélectionnés')
    def unpublish_posts(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} article(s) dépublié(s).")


@admin.register(PhoneVerificationCode)
class PhoneVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('phone', 'code', 'created_at', 'is_used')
    list_filter = ('is_used',)
    readonly_fields = ('phone', 'code', 'created_at', 'is_used')
    ordering = ('-created_at',)


@admin.register(VideoContent)
class VideoContentAdmin(admin.ModelAdmin):
    form = VideoContentAdminForm
    save_on_top = True
    list_display = ('title', 'category', 'video_type_badge', 'login_required', 'is_featured', 'created_at')
    list_filter = ('category', 'login_required', 'is_featured')
    search_fields = ('title', 'description')
    list_editable = ('is_featured', 'login_required')
    readonly_fields = ('media_preview',)
    fieldsets = (
        (None, {'fields': ('title', 'category', 'is_featured', 'login_required')}),
        ('Source vidéo', {
            'fields': ('youtube_url', 'video_file', 'media_preview'),
            'description': (
                'Fournissez SOIT une URL YouTube, SOIT un fichier vidéo (MP4, WebM, OGG). '
                'Si les deux sont fournis, YouTube sera utilisé en priorité.'
            ),
        }),
        ('Détails', {'fields': ('thumbnail', 'description')}),
    )

    @admin.display(description='Type')
    def video_type_badge(self, obj):
        if obj.is_youtube:
            return mark_safe('<span style="color:#cc0000;font-weight:600;">&#9654; YouTube</span>')
        if obj.is_file_video:
            return mark_safe('<span style="color:#006837;font-weight:600;">Fichier</span>')
        return mark_safe('<span style="color:#999;">—</span>')

    @admin.display(description='Aperçu')
    def media_preview(self, obj):
        if not obj.pk:
            return "Sauvegardez d'abord pour voir l'aperçu."
        if obj.is_youtube:
            return format_html(
                '<iframe src="{}" width="400" height="225" frameborder="0" '
                'allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" '
                'allowfullscreen style="border-radius:8px;display:block;"></iframe>',
                obj.get_embed_url(),
            )
        if obj.is_file_video:
            return format_html(
                '<video src="{}" width="400" height="225" controls '
                'style="border-radius:8px;background:#000;display:block;"></video>',
                obj.video_file.url,
            )
        return '—'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.is_youtube and not obj.thumbnail:
            self._auto_fetch_thumbnail(request, obj)

    def _auto_fetch_thumbnail(self, request, obj):
        from django.conf import settings
        import urllib.request
        import urllib.error
        import json
        import os
        from django.core.files.base import ContentFile

        api_key = getattr(settings, 'YOUTUBE_API_KEY', '')
        yt_id = obj.get_youtube_id()
        if not api_key or not yt_id:
            return

        url = (
            f'https://www.googleapis.com/youtube/v3/videos'
            f'?part=snippet&id={yt_id}&key={api_key}'
        )
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
            items = data.get('items', [])
            if not items:
                return
            thumbs = items[0]['snippet']['thumbnails']
            thumb_url = (
                thumbs.get('maxres', thumbs.get('high', thumbs.get('medium', {})))
                .get('url', '')
            )
            if not thumb_url:
                return
            with urllib.request.urlopen(thumb_url, timeout=5) as img_resp:
                img_data = img_resp.read()
            filename = f'yt_{yt_id}.jpg'
            obj.thumbnail.save(filename, ContentFile(img_data), save=True)
            self.message_user(request, f'Miniature récupérée automatiquement depuis YouTube pour « {obj.title} ».')
        except (urllib.error.URLError, KeyError, json.JSONDecodeError):
            pass


@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = ('label', 'value', 'icon', 'order')
    list_editable = ('value', 'order')


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    list_editable = ('is_approved',)
    actions = ['approve_testimonials']

    @admin.action(description="Approuver les témoignages sélectionnés")
    def approve_testimonials(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} témoignage(s) approuvé(s).")


@admin.register(VolunteerTask)
class VolunteerTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'assigned_to', 'deadline', 'created_at')
    list_filter = ('status',)
    list_editable = ('status',)
    autocomplete_fields = ('assigned_to',)


@admin.register(PartnershipRequest)
class PartnershipRequestAdmin(admin.ModelAdmin):
    list_display = ('organization_name', 'contact_name', 'contact_email', 'status', 'created_at')
    list_filter = ('status',)
    list_editable = ('status',)
    readonly_fields = ('created_at',)
    actions = ['approve_requests', 'reject_requests']

    @admin.action(description="Approuver les demandes sélectionnées")
    def approve_requests(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f"{updated} demande(s) approuvée(s).")

    @admin.action(description="Rejeter les demandes sélectionnées")
    def reject_requests(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f"{updated} demande(s) rejetée(s).")


@admin.register(FundingProject)
class FundingProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'goal_amount', 'raised_amount', 'progress_bar', 'is_active')
    list_editable = ('is_active',)

    @admin.display(description='Progression')
    def progress_bar(self, obj):
        pct = obj.progress_percentage
        color = '#006837' if pct < 75 else '#F7941D'
        return format_html(
            '<div style="width:120px;background:#eee;border-radius:4px;">'
            '<div style="width:{pct}%;background:{color};height:14px;border-radius:4px;'
            'text-align:center;color:white;font-size:11px;line-height:14px;">{pct}%</div>'
            '</div>',
            pct=pct, color=color
        )


@admin.register(ActivityReport)
class ActivityReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')


@admin.register(Casting)
class CastingAdmin(admin.ModelAdmin):
    list_display = ('title', 'deadline', 'is_open', 'created_at')
    list_editable = ('is_open',)


@admin.register(DonationRecord)
class DonationRecordAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount_display', 'payment_method', 'confirmed', 'created_at')
    list_filter = ('payment_method', 'confirmed')
    list_editable = ('confirmed',)
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    @admin.display(description='Montant (FCFA)')
    def amount_display(self, obj):
        return f"{int(obj.amount):,} FCFA".replace(',', ' ')


@admin.register(VideoComment)
class VideoCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'video', 'short_text', 'created_at')
    list_filter = ('video',)
    search_fields = ('user__username', 'text')
    readonly_fields = ('created_at',)

    @admin.display(description='Commentaire')
    def short_text(self, obj):
        return obj.text[:80] + '…' if len(obj.text) > 80 else obj.text


@admin.register(CommunityMessage)
class CommunityMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'short_text', 'created_at')
    search_fields = ('user__username', 'text')
    readonly_fields = ('created_at',)

    @admin.display(description='Message')
    def short_text(self, obj):
        return obj.text[:80] + '…' if len(obj.text) > 80 else obj.text


@admin.register(LiveStream)
class LiveStreamAdmin(admin.ModelAdmin):
    list_display  = ('title', 'is_live_badge', 'platform', 'started_at')
    list_editable = ('is_live',) if False else ()  # toggle via action
    readonly_fields = ('started_at',)
    actions = ['go_live', 'go_offline']
    fields  = ('title', 'platform', 'stream_url', 'description', 'is_live', 'started_at', 'thumbnail')

    @admin.display(description='Statut', boolean=False)
    def is_live_badge(self, obj):
        if obj.is_live:
            return mark_safe('<span style="color:#fff;background:#dc2626;padding:2px 10px;border-radius:20px;font-size:.75rem;font-weight:700;">&#128308; EN DIRECT</span>')
        return mark_safe('<span style="color:#6b7280;font-size:.8rem;">&#9899; Hors ligne</span>')

    @admin.action(description='▶ Mettre en direct')
    def go_live(self, request, queryset):
        from django.utils import timezone
        LiveStream.objects.filter(is_live=True).update(is_live=False)
        queryset.update(is_live=True, started_at=timezone.now())

    @admin.action(description='⏹ Arrêter le direct')
    def go_offline(self, request, queryset):
        queryset.update(is_live=False)


@admin.register(EmissionSlot)
class EmissionSlotAdmin(admin.ModelAdmin):
    list_display   = ('title', 'date', 'start_time', 'end_time', 'category', 'presenter', 'is_highlighted')
    list_filter    = ('date', 'category', 'is_highlighted')
    list_editable  = ('is_highlighted',)
    search_fields  = ('title', 'presenter')
    date_hierarchy = 'date'
    ordering       = ('date', 'start_time')
    fieldsets = (
        (None, {'fields': ('title', 'date', 'start_time', 'end_time', 'category')}),
        ('Détails', {'fields': ('presenter', 'description', 'thumbnail', 'is_highlighted'), 'classes': ('collapse',)}),
    )


# ──────────────────────────────────────────────────────────────────────────────
# BIBLIOTHÈQUE D'ÉTUDE
# ──────────────────────────────────────────────────────────────────────────────

class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 4
    fields = ('text', 'is_correct', 'order')


class QuizQuestionInline(admin.StackedInline):
    model = QuizQuestion
    extra = 1
    fields = ('text', 'explanation', 'order', 'points')
    show_change_link = True


class CourseResourceInline(admin.TabularInline):
    model = CourseResource
    extra = 1
    fields = ('title', 'resource_type', 'file', 'video_url', 'order')
    show_change_link = True


@admin.register(StudyCourse)
class StudyCourseAdmin(admin.ModelAdmin):
    list_display  = ('title', 'instructor', 'resource_count', 'enrolled_count', 'pass_score', 'is_published', 'created_at')
    list_filter   = ('is_published',)
    list_editable = ('is_published',)
    search_fields = ('title', 'description', 'instructor')
    inlines       = [CourseResourceInline]
    fieldsets = (
        (None, {'fields': ('title', 'instructor', 'thumbnail', 'is_published', 'pass_score')}),
        ('Description', {'fields': ('description',)}),
    )
    actions = ['publish_courses', 'unpublish_courses']

    @admin.display(description='Ressources')
    def resource_count(self, obj):
        return obj.resources.count()

    @admin.display(description='Inscrits')
    def enrolled_count(self, obj):
        return obj.enrollments.count()

    @admin.action(description='✅ Publier les formations sélectionnées')
    def publish_courses(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} formation(s) publiée(s).")

    @admin.action(description='⏸ Dépublier les formations sélectionnées')
    def unpublish_courses(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} formation(s) dépubliée(s).")


@admin.register(CourseResource)
class CourseResourceAdmin(admin.ModelAdmin):
    list_display  = ('title', 'course', 'resource_type', 'order', 'has_quiz')
    list_filter   = ('resource_type', 'course')
    search_fields = ('title', 'course__title')
    list_select_related = ('course',)
    ordering      = ('course', 'order')

    @admin.display(description='Quiz', boolean=True)
    def has_quiz(self, obj):
        return hasattr(obj, 'quiz')


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 0
    readonly_fields = ('question', 'selected_choice')
    can_delete = False


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display  = ('title', 'resource', 'course', 'question_count', 'pass_score', 'time_limit_minutes')
    list_filter   = ('pass_score',)
    search_fields = ('title',)
    inlines       = [QuizQuestionInline]

    @admin.display(description='Questions')
    def question_count(self, obj):
        return obj.questions.count()


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('text_short', 'quiz', 'order', 'points')
    list_filter  = ('quiz',)
    inlines      = [QuizChoiceInline]
    ordering     = ('quiz', 'order')

    @admin.display(description='Question')
    def text_short(self, obj):
        return obj.text[:80] + '…' if len(obj.text) > 80 else obj.text


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display    = ('user', 'quiz', 'score', 'passed', 'started_at', 'completed_at')
    list_filter     = ('passed', 'quiz')
    readonly_fields = ('user', 'quiz', 'score', 'passed', 'started_at', 'completed_at')
    inlines         = [QuizAnswerInline]
    search_fields   = ('user__username',)


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display  = ('user', 'course', 'progress_pct', 'is_completed', 'enrolled_at')
    list_filter   = ('course',)
    readonly_fields = ('enrolled_at', 'completed_at')
    search_fields = ('user__username', 'course__title')

    @admin.display(description='Progression')
    def progress_pct(self, obj):
        pct = obj.progress_pct
        color = '#006837' if pct == 100 else '#F7941D'
        return format_html(
            '<div style="width:100px;background:#eee;border-radius:4px;">'
            '<div style="width:{pct}%;background:{color};height:14px;border-radius:4px;'
            'text-align:center;color:white;font-size:11px;line-height:14px;">{pct}%</div>'
            '</div>',
            pct=pct, color=color
        )

    @admin.display(description='Terminé', boolean=True)
    def is_completed(self, obj):
        return obj.is_completed


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display  = ('certificate_number', 'user', 'course', 'score_display', 'issued_at')
    list_filter   = ('course',)
    readonly_fields = ('certificate_number', 'issued_at', 'attempt')
    search_fields = ('user__username', 'course__title', 'certificate_number')
    ordering      = ('-issued_at',)

    @admin.display(description='Score')
    def score_display(self, obj):
        if obj.attempt:
            return f"{obj.attempt.score}/100"
        return '—'


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display  = ('email', 'subscribed_at', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('email',)
    ordering      = ('-subscribed_at',)
    readonly_fields = ('subscribed_at',)
