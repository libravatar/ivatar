# -*- coding: utf-8 -*-
"""
ivatar/tools URL configuration
"""

from django.urls import path, re_path
from .views import CheckView, CheckDomainView

urlpatterns = [  # pylint: disable=invalid-name
    path("check/", CheckView.as_view(), name="tools_check"),
    path("check_domain/", CheckDomainView.as_view(), name="tools_check_domain"),
    re_path("check_domain$", CheckDomainView.as_view(), name="tools_check_domain"),
]
