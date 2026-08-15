from timetracker.models import RecordedApp , RecordedWebsite
from rest_framework import serializers


class AppSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RecordedApp
        fields = ['id', 'name','is_browser']


class WebsiteSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RecordedWebsite
        fields = ['id', 'name','domain']