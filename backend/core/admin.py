from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class ChatAdminSite(AdminSite):
    site_header = _('Chat Application Admin')
    site_title = _('Chat Admin')
    index_title = _('Welcome to Chat Administration')

# You can replace the default admin site if you want
# admin.site = ChatAdminSite(name='chatadmin')
