# -*- coding: utf-8 -*-
"""
ivatar URL configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import url
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView
from ivatar import settings
from .views import AvatarImageView, GravatarProxyView, StatsView

urlpatterns = [  # pylint: disable=invalid-name
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    url("openid/", include("django_openid_auth.urls")),
    url("tools/", include("ivatar.tools.urls")),
    url(r"avatar/(?P<digest>\w{64})", AvatarImageView.as_view(), name="avatar_view"),
    url(r"avatar/(?P<digest>\w{32})", AvatarImageView.as_view(), name="avatar_view"),
    url(r"avatar/$", AvatarImageView.as_view(), name="avatar_view"),
    url(
        r"avatar/(?P<digest>\w*)",
        RedirectView.as_view(url="/static/img/deadbeef.png"),
        name="invalid_hash",
    ),
    url(
        r"gravatarproxy/(?P<digest>\w*)",
        GravatarProxyView.as_view(),
        name="gravatarproxy",
    ),
    url(
        "description/",
        TemplateView.as_view(template_name="description.html"),
        name="description",
    ),
    # The following two are TODO TODO TODO TODO TODO
    url(
        "run_your_own/",
        TemplateView.as_view(template_name="run_your_own.html"),
        name="run_your_own",
    ),
    url(
        "features/",
        TemplateView.as_view(template_name="features.html"),
        name="features",
    ),
    url(
        "security/",
        TemplateView.as_view(template_name="security.html"),
        name="security",
    ),
    url("privacy/", TemplateView.as_view(template_name="privacy.html"), name="privacy"),
    url("contact/", TemplateView.as_view(template_name="contact.html"), name="contact"),
    path("talk_to_us/", RedirectView.as_view(url="/contact"), name="talk_to_us"),
    url("stats/", StatsView.as_view(), name="stats"),
]

MAINTENANCE = False
try:
    if settings.MAINTENANCE:
        MAINTENANCE = True
except:  # pylint: disable=bare-except
    pass

if MAINTENANCE:
    urlpatterns.append(
        url("", TemplateView.as_view(template_name="maintenance.html"), name="home")
    )
    urlpatterns.insert(3, url("accounts/", RedirectView.as_view(url="/")))
else:
    urlpatterns.append(
        url("", TemplateView.as_view(template_name="home.html"), name="home")
    )
    urlpatterns.insert(3, url("accounts/", include("ivatar.ivataraccount.urls")))


urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
