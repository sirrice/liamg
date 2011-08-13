from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('emailanalysis.views',
    (r'^$', 'index'),
    (r'^(?P<datatype>[\w]+)/json/$', 'getjson'),
    (r'^sendmail/$', 'sendmail'),
    (r'^sendmail/send/$', 'sendmail'),
    # Examples:
    # url(r'^$', 'liamgwebapp.views.home', name='home'),
    # url(r'^liamgwebapp/', include('liamgwebapp.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)
