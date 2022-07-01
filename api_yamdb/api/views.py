from rest_framework import filters, generics, mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import models
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from .filters import TitleFilter
from api.service import get_random_number
from reviews.models import Category, Genre, Review, Title
from user.models import User
from .permissions import (
    AdminOrReadOnly, GetAuthenticatedPatchAdminOrAuthor,
    OnlyReadOrСhangeAuthorAdminModerator,
    OwnIsAuthenticatedAndIsAdmin)
from .paginations import CustomPagination
from .serializers import (
    AuthSerializer, CategorySerializer,
    CommentSerializer, GenreSerializer,
    GenreSerializer, ReadTitleSerializer,
    ReviewSerializer, TokenSerializer,
    UserSerializer, UserMeSerializer,
    WriteTitleSerializer)


class UserViewSet(viewsets.ModelViewSet):
    """Вьюшка для просмотра, добавление, редактирования юзеров"""
    permission_classes = [OwnIsAuthenticatedAndIsAdmin]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    lookup_field = 'username'
    search_fields = ['username']
    pagination_class = CustomPagination


class DetailView(APIView):
    """Получение и изменение данных своей учетной записи"""
    permission_classes = [GetAuthenticatedPatchAdminOrAuthor]

    def get(self, request, format=None):
        user = get_object_or_404(User, username=request.user.username)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = UserMeSerializer(
            user,
            data=request.data,
            partial=True,
            context={'role': request.user.role}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AuthViewRegister(generics.CreateAPIView):
    """Регистрация пользователя."""
    queryset = User.objects.all()
    serializer_class = AuthSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super(AuthViewRegister, self).get_serializer_context()
        code = get_random_number()
        context.update({"code": code})
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_200_OK, headers=headers)


class TokenViewGet(APIView):
    """Получаем токен."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateDeleteListViewSet(
        mixins.CreateModelMixin, mixins.ListModelMixin,
        mixins.DestroyModelMixin, viewsets.GenericViewSet):
    pass


class CategoryViewSet(CreateDeleteListViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (AdminOrReadOnly,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    lookup_field = 'slug'


class GenreViewSet(CreateDeleteListViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (AdminOrReadOnly,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    lookup_field = 'slug'


class TitleViewSet(viewsets.ModelViewSet):
    queryset = Title.objects.all()
    serializer_class = WriteTitleSerializer
    permission_classes = (AdminOrReadOnly,)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TitleFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return WriteTitleSerializer
        return ReadTitleSerializer

    def get_queryset(self):
        new_queryset = Title.objects.annotate(
            rating=models.Sum(models.F('reviews__score'))
            / models.Count(models.F('reviews'))
        )
        return new_queryset.order_by('name', 'category', '-year')


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = (OnlyReadOrСhangeAuthorAdminModerator,)
    pagination_class = CustomPagination

    def get_queryset(self):
        new_queryset = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        return new_queryset.reviews.all()

    def perform_create(self, serializer):
        instance = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        serializer.save(author=self.request.user, title=instance)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = (OnlyReadOrСhangeAuthorAdminModerator,)
    pagination_class = CustomPagination

    def get_queryset(self):
        title_id = self.kwargs.get('title_id')
        review_id = self.kwargs.get('review_id')
        new_queryset = get_object_or_404(
            Review,
            id=review_id,
            title_id=title_id)
        return new_queryset.comments.all()

    def perform_create(self, serializer):
        instance = get_object_or_404(
            Review,
            id=self.kwargs.get('review_id'),
            title_id=self.kwargs.get('title_id'))
        serializer.save(author=self.request.user, review=instance)
