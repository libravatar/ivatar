# -*- coding: utf-8 -*-
"""
ivatar URL configuration
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView
from ivatar import settings
from .views import AvatarImageView, GravatarProxyView, StatsView

urlpatterns = [  # pylint: disable=invalid-name
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("openid/", include("django_openid_auth.urls")),
    path("tools/", include("ivatar.tools.urls")),
    re_path(
        r"avatar/(?P<digest>\w{64})", AvatarImageView.as_view(), name="avatar_view"
    ),
    re_path(
        r"avatar/(?P<digest>\w{32})", AvatarImageView.as_view(), name="avatar_view"
    ),
    re_path(r"avatar/$", AvatarImageView.as_view(), name="avatar_view"),
    re_path(
        r"avatar/(?P<digest>\w*)",
        RedirectView.as_view(url="/static/img/deadbeef.png"),
        name="invalid_hash",
    ),
    re_path(
        r"gravatarproxy/(?P<digest>\w*)",
        GravatarProxyView.as_view(),
        name="gravatarproxy",
    ),
    path(
        "description/",
        TemplateView.as_view(template_name="description.html"),
        name="description",
    ),
    # The following two are TODO TODO TODO TODO TODO
    path(
        "run_your_own/",
        TemplateView.as_view(template_name="run_your_own.html"),
        name="run_your_own",
    ),
    path(
        "features/",
        TemplateView.as_view(template_name="features.html"),
        name="features",
    ),
    path(
        "security/",
        TemplateView.as_view(template_name="security.html"),
        name="security",
    ),
    path(
        "privacy/", TemplateView.as_view(template_name="privacy.html"), name="privacy"
    ),
    path(
        "contact/", TemplateView.as_view(template_name="contact.html"), name="contact"
    ),
    path("talk_to_us/", RedirectView.as_view(url="/contact"), name="talk_to_us"),
    path("stats/", StatsView.as_view(), name="stats"),
]

MAINTENANCE = False
try:
    if settings.MAINTENANCE:
        MAINTENANCE = True
except Exception:  # pylint: disable=bare-except
    pass

if MAINTENANCE:
    urlpatterns.append(
        path("", TemplateView.as_view(template_name="maintenance.html"), name="home")
    )
    urlpatterns.insert(3, path("accounts/", RedirectView.as_view(url="/")))
else:
    urlpatterns.append(
        path("", TemplateView.as_view(template_name="home.html"), name="home")
    )
    urlpatterns.insert(3, path("accounts/", include("ivatar.ivataraccount.urls")))

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
