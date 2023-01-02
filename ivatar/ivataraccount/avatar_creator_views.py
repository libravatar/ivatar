# -*- coding: utf-8 -*-
"""
View classes for the avatar creator
"""
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic.base import View, TemplateView
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy
from jinja2 import Environment, PackageLoader
import py_avataaars as pa


@method_decorator(login_required, name="dispatch")
class AvatarCreatorView(TemplateView):
    """
    View class responsible for handling avatar creation
    """

    template_name = "avatar_creator.html"

    def get(self, request, *args, **kwargs):
        """
        Handle get for create view
        """
        if request.user:
            if not request.user.is_authenticated:
                return HttpResponseRedirect(reverse_lazy("profile"))

        return super().get(self, request, args, kwargs)

    def get_context_data(self, **kwargs):
        """
        Provide additional context data
        """
        context = super().get_context_data(**kwargs)
        context["SkinColor"] = list(pa.SkinColor)
        context["HairColor"] = list(pa.HairColor)
        context["FacialHairType"] = list(pa.FacialHairType)
        context["TopType"] = list(pa.TopType)
        context["HatColor"] = list(pa.Color)
        context["MouthType"] = list(pa.MouthType)
        context["EyesType"] = list(pa.EyesType)
        context["EyebrowType"] = list(pa.EyebrowType)
        context["NoseType"] = list(pa.NoseType)
        context["AccessoriesType"] = list(pa.AccessoriesType)
        context["ClotheType"] = list(pa.ClotheType)
        context["ClotheColor"] = list(pa.Color)
        context["ClotheGraphicType"] = list(pa.ClotheGraphicType)
        return context


@method_decorator(login_required, name="dispatch")
class AvatarView(View):
    """
    View class responsible for handling avatar view
    """

    def get(
        self, request, *args, **kwargs
    ):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements,unused-argument
        """
        Handle get for create view
        """
        output_format = "svg+xml"

        avatar_style = list(pa.AvatarStyle)[0]
        skin_color = list(pa.SkinColor)[0]
        hair_color = list(pa.HairColor)[0]
        facial_hair_type = list(pa.FacialHairType)[0]
        top_type = pa.TopType.SHORT_HAIR_SHORT_FLAT
        hat_color = list(pa.Color)[0]
        mouth_type = list(pa.MouthType)[0]
        eyes_type = list(pa.EyesType)[0]
        eyebrow_type = list(pa.EyebrowType)[0]
        nose_type = list(pa.NoseType)[0]
        accessories_type = list(pa.AccessoriesType)[0]
        clothe_type = list(pa.ClotheType)[0]
        clothe_color = list(pa.Color)[0]
        clothe_graphic_type = list(pa.ClotheGraphicType)[0]

        if "avatar_style" in request.GET:
            avatar_style = list(pa.AvatarStyle)[int(request.GET["avatar_style"])]
        if "skin_color" in request.GET:
            skin_color = list(pa.SkinColor)[int(request.GET["skin_color"])]
        if "hair_color" in request.GET:
            hair_color = list(pa.HairColor)[int(request.GET["hair_color"])]
        if "facial_hair_type" in request.GET:
            facial_hair_type = list(pa.FacialHairType)[
                int(request.GET["facial_hair_type"])
            ]
        if "facial_hair_color" in request.GET:
            facial_hair_color = list(pa.HairColor)[
                int(request.GET["facial_hair_color"])
            ]
        if "top_type" in request.GET:
            top_type = list(pa.TopType)[int(request.GET["top_type"])]
        if "hat_color" in request.GET:
            hat_color = list(pa.Color)[int(request.GET["hat_color"])]
        if "mouth_type" in request.GET:
            mouth_type = list(pa.MouthType)[int(request.GET["mouth_type"])]
        if "eyes_type" in request.GET:
            eyes_type = list(pa.EyesType)[int(request.GET["eyes_type"])]
        if "eyebrow_type" in request.GET:
            eyebrow_type = list(pa.EyebrowType)[int(request.GET["eyebrow_type"])]
        if "nose_type" in request.GET:
            nose_type = list(pa.NoseType)[int(request.GET["nose_type"])]
        if "accessories_type" in request.GET:
            accessories_type = list(pa.AccessoriesType)[
                int(request.GET["accessories_type"])
            ]
        if "clothe_type" in request.GET:
            clothe_type = list(pa.ClotheType)[int(request.GET["clothe_type"])]
        if "clothe_color" in request.GET:
            clothe_color = list(pa.Color)[int(request.GET["clothe_color"])]
        if "clothe_graphic_type" in request.GET:
            clothe_graphic_type = list(pa.ClotheGraphicType)[
                int(request.GET["clothe_graphic_type"])
            ]
        if "format" in request.GET:
            if request.GET["format"] == "png":
                output_format = request.GET["format"]
            elif request.GET["format"] in ("svg", "svg+xml"):
                output_format = "svg+xml"
            else:
                print(
                    "Format: '%s' isn't supported" % request.GET["format"]
                )  # pylint: disable=consider-using-f-string

        avatar = pa.PyAvataaar(
            style=avatar_style,
            skin_color=skin_color,
            hair_color=hair_color,
            facial_hair_type=facial_hair_type,
            facial_hair_color=facial_hair_color,
            top_type=top_type,
            hat_color=hat_color,
            mouth_type=mouth_type,
            eye_type=eyes_type,
            eyebrow_type=eyebrow_type,
            nose_type=nose_type,
            accessories_type=accessories_type,
            clothe_type=clothe_type,
            clothe_color=clothe_color,
            clothe_graphic_type=clothe_graphic_type,
        )
        if output_format == "png":
            return HttpResponse(avatar.render_png(), content_type="image/png")

        return HttpResponse(avatar.render_svg(), content_type="image/svg+xml")


@method_decorator(login_required, name="dispatch")
class AvatarItemView(View):
    """
    View class responsible for providing access to single avatar items
    """

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Handle get for create view
        """
        item = request.GET["item"]

        env = Environment(
            loader=PackageLoader("py_avataaars", "templates"),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True,
            keep_trailing_newline=False,
            extensions=[],
        )
        template = env.get_template(item)

        def uni(attr):  # pylint: disable=unused-argument
            return None

        rendered_template = template.render(
            unique_id=uni,
            template_path=pa.PyAvataaar._PyAvataaar__template_path,  # pylint: disable=protected-access
            template_name=pa.PyAvataaar._PyAvataaar__template_name,  # pylint: disable=protected-access
            facial_hair_type=pa.FacialHairType.DEFAULT,
            hat_color=pa.Color.BLACK,
            clothe_color=pa.Color.HEATHER,
            hair_color=pa.HairColor.BROWN,
            facial_hair_color=pa.HairColor.BROWN,
            clothe_graphic_type=pa.ClotheGraphicType.BAT,
            accessories_type=pa.AccessoriesType.DEFAULT,
        ).replace("\n", "")
        rendered_template = (
            '<?xml version="1.0" encoding="utf-8" ?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg width="280px" height="280px" viewBox="-6 0 274 280" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
            + rendered_template
            + "</svg>"
        )  # pylint: disable=line-too-long

        return HttpResponse(rendered_template, content_type="image/svg+xml")
