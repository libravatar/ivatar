'''
View classes for ivatar/tools/
'''
from django.views.generic.edit import FormView
from django.urls import reverse_lazy as reverse
from django.shortcuts import render

import DNS

from libravatar import libravatar_url, parse_user_identity
from libravatar import SECURE_BASE_URL as LIBRAVATAR_SECURE_BASE_URL
from libravatar import BASE_URL as LIBRAVATAR_BASE_URL
import hashlib

from .forms import CheckDomainForm, CheckForm
from ivatar.settings import SECURE_BASE_URL, BASE_URL


class CheckDomainView(FormView):
    '''
    View class for checking a domain
    '''
    template_name = 'check_domain.html'
    form_class = CheckDomainForm
    success_url = reverse('tools_check_domain')

    def form_valid(self, form):
        result = {}
        super().form_valid(form)
        domain = form.cleaned_data['domain']
        result['avatar_server_http'] = lookup_avatar_server(domain, False)
        if result['avatar_server_http']:
            result['avatar_server_http_ipv4'] = lookup_ip_address(result['avatar_server_http'], False)
            result['avatar_server_http_ipv6'] = lookup_ip_address(result['avatar_server_http'], True)
        result['avatar_server_https'] = lookup_avatar_server(domain, True)
        if result['avatar_server_https']:
            result['avatar_server_https_ipv4'] = lookup_ip_address(result['avatar_server_https'], False)
            result['avatar_server_https_ipv6'] = lookup_ip_address(result['avatar_server_https'], True)
        return render(self.request, self.template_name, {
            'form': form,
            'result': result,
        })

class CheckView(FormView):
    '''
    View class for checking an e-mail or openid address
    '''
    template_name = 'check.html'
    form_class = CheckForm
    success_url = reverse('tools_check')

    def form_valid(self, form):
        mailurl = None
        openidurl = None
        mailurl_secure = None
        mailurl_secure_256 = None
        openidurl_secure = None
        mail_hash = None
        mail_hash256 = None
        openid_hash = None
        size = 80

        super().form_valid(form)

        if form.cleaned_data['default_url']:
            default_url = form.cleaned_data['default_url']
        elif form.cleaned_data['default_opt'] and form.cleaned_data['default_opt'] != 'none':
            default_url = form.cleaned_data['default_opt']
        else:
            default_url = None

        if 'size' in form.cleaned_data:
            size = form.cleaned_data['size']
        if form.cleaned_data['mail']:
            mailurl = libravatar_url(
              email=form.cleaned_data['mail'],
              size=size,
              default=default_url)
            mailurl = mailurl.replace(LIBRAVATAR_BASE_URL, BASE_URL)
            mailurl_secure = libravatar_url(
              email=form.cleaned_data['mail'],
              size=size,
              https=True,
              default=default_url)
            mailurl_secure = mailurl_secure.replace(
              LIBRAVATAR_SECURE_BASE_URL,
              SECURE_BASE_URL)
            mail_hash = parse_user_identity(
              email=form.cleaned_data['mail'],
              openid=None)[0]
            hash_obj = hashlib.new('sha256')
            hash_obj.update(form.cleaned_data['mail'].encode('utf-8'))
            mail_hash256 = hash_obj.hexdigest()
            mailurl_secure_256 = mailurl_secure.replace(
                mail_hash,
                mail_hash256)
        if form.cleaned_data['openid']:
            if not form.cleaned_data['openid'].startswith('http://') and not form.cleaned_data['openid'].startswith('https://'):
                form.cleaned_data['openid'] = 'http://%s' % form.cleaned_data['openid']
            openidurl = libravatar_url(
              openid=form.cleaned_data['openid'],
              size=size,
              default=default_url)
            openidurl = openidurl.replace(LIBRAVATAR_BASE_URL, BASE_URL)
            openidurl_secure = libravatar_url(
              openid=form.cleaned_data['openid'],
              size=size,
              https=True,
              default=default_url)
            openidurl_secure = openidurl_secure.replace(
              LIBRAVATAR_SECURE_BASE_URL,
              SECURE_BASE_URL)
            openid_hash = parse_user_identity(
              openid=form.cleaned_data['openid'],
              email=None)[0]

        return render(self.request, self.template_name, {
            'form': form,
            'mailurl': mailurl,
            'openidurl': openidurl,
            'mailurl_secure': mailurl_secure,
            'mailurl_secure_256': mailurl_secure_256,
            'openidurl_secure': openidurl_secure,
            'mail_hash': mail_hash,
            'mail_hash256': mail_hash256,
            'openid_hash': openid_hash,
            'size': size,
        })


def lookup_avatar_server(domain, https):
    '''
    Extract the avatar server from an SRV record in the DNS zone

    The SRV records should look like this:

       _avatars._tcp.example.com.     IN SRV 0 0 80  avatars.example.com
       _avatars-sec._tcp.example.com. IN SRV 0 0 443 avatars.example.com
    '''

    if domain and len(domain) > 60:
        domain = domain[:60]

    service_name = None
    if https:
        service_name = "_avatars-sec._tcp.%s" % domain
    else:
        service_name = "_avatars._tcp.%s" % domain

    DNS.DiscoverNameServers()
    try:
        dns_request = DNS.Request(name=service_name, qtype='SRV').req()
    except DNS.DNSError as message:
        print("DNS Error: %s (%s)" % (message, domain))
        return None

    if dns_request.header['status'] == 'NXDOMAIN':
        # Not an error, but no point in going any further
        return None

    if dns_request.header['status'] != 'NOERROR':
        print("DNS Error: status=%s (%s)" % (dns_request.header['status'], domain))
        return None

    records = []
    for answer in dns_request.answers:
        if ('data' not in answer) or (not answer['data']) or (not answer['typename']) or (answer['typename'] != 'SRV'):
            continue

        record = {'priority': int(answer['data'][0]), 'weight': int(answer['data'][1]),
                  'port': int(answer['data'][2]), 'target': answer['data'][3]}

        records.append(record)

    target, port = srv_hostname(records)

    if target and ((https and port != 443) or (not https and port != 80)):
        return "%s:%s" % (target, port)

    return target


def srv_hostname(records):
    '''
    Return the right (target, port) pair from a list of SRV records.
    '''

    if len(records) < 1:
        return (None, None)

    if len(records) == 1:
        ret = records[0]
        return (ret['target'], ret['port'])

    # Keep only the servers in the top priority
    priority_records = []
    total_weight = 0
    top_priority = records[0]['priority']  # highest priority = lowest number

    for ret in records:
        if ret['priority'] > top_priority:
            # ignore the record (ret has lower priority)
            continue
        elif ret['priority'] < top_priority:
            # reset the aretay (ret has higher priority)
            top_priority = ret['priority']
            total_weight = 0
            priority_records = []

        total_weight += ret['weight']

        if ret['weight'] > 0:
            priority_records.append((total_weight, ret))
        else:
            # zero-weigth elements must come first
            priority_records.insert(0, (0, ret))

    if len(priority_records) == 1:
        unused, ret = priority_records[0]
        return (ret['target'], ret['port'])

    # Select first record according to RFC2782 weight ordering algorithm (page 3)
    random_number = random.randint(0, total_weight)

    for record in priority_records:
        weighted_index, ret = record

        if weighted_index >= random_number:
            return (ret['target'], ret['port'])

    print('There is something wrong with our SRV weight ordering algorithm')
    return (None, None)


def lookup_ip_address(hostname, ipv6):
    """
    Try to get IPv4 or IPv6 addresses for the given hostname
    """

    DNS.DiscoverNameServers()
    try:
        if ipv6:
            dns_request = DNS.Request(name=hostname, qtype=DNS.Type.AAAA).req()
        else:
            dns_request = DNS.Request(name=hostname, qtype=DNS.Type.A).req()
    except DNS.DNSError as message:
        print("DNS Error: %s (%s)" % (message, hostname))
        return None

    if dns_request.header['status'] != 'NOERROR':
        print("DNS Error: status=%s (%s)" % (dns_request.header['status'], hostname))
        return None

    for answer in dns_request.answers:
        if ('data' not in answer) or (not answer['data']):
            continue
        if (ipv6 and answer['typename'] != 'AAAA') or (not ipv6 and answer['typename'] != 'A'):
            continue  # skip CNAME records

        if ipv6:
            return inet_ntop(AF_INET6, answer['data'])
        else:
            return answer['data']

    return None
