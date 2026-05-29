from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),

    # WebTV
    path('webtv/', views.VideoListView.as_view(), name='video_list'),
    path('webtv/<int:pk>/', views.VideoDetailView.as_view(), name='video_detail'),
    path('webtv/<int:pk>/comments/', views.VideoCommentView.as_view(), name='video_comments'),
    path('webtv/<int:pk>/like/', views.VideoLikeView.as_view(), name='video_like'),

    # Don
    path('don/', views.DonationPageView.as_view(), name='donation'),

    # Live streaming
    path('live/', views.LiveView.as_view(), name='live'),
    path('live/status/', views.LiveStatusAPIView.as_view(), name='live_status'),
    path('live/control/', views.LiveControlView.as_view(), name='live_control'),

    # Communauté
    path('communaute/', views.CommunityView.as_view(), name='community'),
    path('communaute/messages/', views.CommunityMessageView.as_view(), name='community_messages'),
    path('communaute/messages/<int:pk>/', views.CommunityMessageDetailView.as_view(), name='community_message_detail'),

    # Dashboards
    path('dashboard/', views.DashboardRedirectView.as_view(), name='dashboard_redirect'),
    path('dashboard/partenaire/', views.PartnerDashboardView.as_view(), name='partner_dashboard'),
    path('dashboard/visiteur/', views.VisitorDashboardView.as_view(), name='visitor_dashboard'),
    path('dashboard/benevole/', views.VolunteerDashboardView.as_view(), name='volunteer_dashboard'),

    # Contact / Auth
    path('partenariat/', views.PartnershipRequestView.as_view(), name='partnership_request'),
    path('inscription/', views.RegisterView.as_view(), name='register'),
    path('compte/attente/', views.PendingApprovalView.as_view(), name='pending_approval'),

    # Connexion téléphone OTP
    path('accounts/phone/', views.PhoneLoginView.as_view(), name='phone_login'),
    path('accounts/phone/verifier/', views.PhoneVerifyView.as_view(), name='phone_verify'),

    # Google OAuth
    path('accounts/google/', views.GoogleLoginView.as_view(), name='google_login'),
    path('accounts/google/callback/', views.GoogleCallbackView.as_view(), name='google_callback'),

    # Blog
    path('blog/', views.BlogListView.as_view(), name='blog_list'),
    path('blog/<slug:slug>/', views.BlogDetailView.as_view(), name='blog_detail'),

    # Bibliothèque d'étude
    path('bibliotheque/', views.StudyLibraryView.as_view(), name='study_library'),
    path('bibliotheque/<int:pk>/', views.CourseDetailView.as_view(), name='study_course'),
    path('bibliotheque/<int:course_pk>/ressource/<int:pk>/', views.ResourceViewerView.as_view(), name='study_resource'),
    path('bibliotheque/<int:course_pk>/ressource/<int:pk>/quiz/', views.QuizView.as_view(), name='study_quiz'),
    path('bibliotheque/<int:course_pk>/ressource/<int:pk>/quiz/<int:attempt_pk>/resultat/', views.QuizResultView.as_view(), name='study_quiz_result'),
    path('bibliotheque/<int:course_pk>/examen/', views.FinalExamView.as_view(), name='study_final_exam'),
    path('bibliotheque/<int:course_pk>/examen/<int:attempt_pk>/resultat/', views.ExamResultView.as_view(), name='study_exam_result'),
    path('bibliotheque/<int:course_pk>/certificat/', views.CertificateView.as_view(), name='study_certificate'),
]
