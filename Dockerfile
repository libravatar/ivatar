FROM quay.io/rhn_support_ofalk/fedora37-python3
LABEL maintainer Oliver Falk <oliver@linux-kernel.at>
EXPOSE 8081

ADD . /opt/ivatar-devel

WORKDIR /opt/ivatar-devel

RUN pip3 install pip --upgrade \
 && virtualenv .virtualenv \
 && source .virtualenv/bin/activate \
 && pip3 install Pillow \
 && pip3 install -r requirements.txt && pip3 install python-coveralls coverage pycco django_coverage_plugin

RUN echo "DEBUG = True" >> /opt/ivatar-devel/config_local.py
RUN echo "EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'" >> /opt/ivatar-devel/config_local.py
RUN source .virtualenv/bin/activate python3 manage.py migrate && python3 manage.py collectstatic --noinput \
 && echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@local.tld', 'admin')" | python manage.py shell
ENTRYPOINT source .virtualenv/bin/activate && python3 ./manage.py runserver 0:8081
