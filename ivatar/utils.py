'''
Simple module providing reusable random_string function
'''
import random
import string


def random_string(length=10):
    '''
    Return some random string with default length 10
    '''
    return ''.join(random.SystemRandom().choice(
        string.ascii_lowercase + string.digits) for _ in range(length))


def openid_variations(openid):
    '''
    Return the various OpenID variations, ALWAYS in the same order:
    - http w/ trailing slash
    - http w/o trailing slash
    - https w/ trailing slash
    - https w/o trailing slash
    '''

    # Make the 'base' version: http w/ trailing slash
    if openid.startswith('https://'):
        openid = openid.replace('https://', 'http://')
    if openid[-1] != '/':
        openid = openid + '/'

    # http w/o trailing slash
    var1 = openid[0:-1]
    var2 = openid.replace('http://', 'https://')
    var3 = var2[0:-1]
    return (openid, var1, var2, var3)
