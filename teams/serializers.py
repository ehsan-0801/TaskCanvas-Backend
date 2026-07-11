from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Board, BoardAccess, Team, TeamMembership


class TeamMembershipSerializer(serializers.ModelSerializer):
    """A member of a team, flattened to the fields the UI needs."""

    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    name = serializers.CharField(source='user.first_name', read_only=True)

    class Meta:
        model = TeamMembership
        fields = ['user_id', 'email', 'name', 'role', 'created_at']


class AddMemberSerializer(serializers.Serializer):
    """Owner adds a member by email + password. Creates the account if the email
    is new, otherwise just attaches the existing user to the team."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        email = attrs['email'].strip().lower()
        existing = User.objects.filter(email__iexact=email).first()
        if existing is None:
            password = attrs.get('password')
            if not password:
                raise serializers.ValidationError(
                    {'password': 'A password is required to create a new user.'}
                )
            validate_password(password)
        attrs['email'] = email
        attrs['existing_user'] = existing
        return attrs


class BoardAccessSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = BoardAccess
        fields = ['id', 'user_id', 'email', 'created_at']
        read_only_fields = fields


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ['id', 'team', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']


class TeamSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'owner', 'role', 'member_count', 'created_at']
        read_only_fields = ['id', 'owner', 'created_at']

    def get_role(self, team):
        user = self.context['request'].user
        return 'owner' if team.owner_id == user.id else 'member'

    def get_member_count(self, team):
        return team.memberships.count()
