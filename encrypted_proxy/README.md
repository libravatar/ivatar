The code in here should be able to help to build up some encrypting proxy.

If your app uses a lot of libravatar and therefore has to do a lot of DNS
lookups, change your app in such a way, that it encodes the mail address,
sends it over to the proxy, which will decrypt it, do the DNS lookup and
return the image binary.

No guarantee for this code. It's untested and just provided as example.
