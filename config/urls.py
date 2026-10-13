from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from core.sitemaps import BetCodeSitemap, StaticViewSitemap

admin.site.site_header = 'TU SURE — Admin'
admin.site.site_title = 'TU SURE Admin'
admin.site.index_title = 'Control Panel'

sitemaps = {
    'static': StaticViewSitemap,
    'betcodes': BetCodeSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('', include('subscriptions.urls')),
    path('', include('betting.urls')),
    path('payments/', include('payments.urls')),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)