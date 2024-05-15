from django.urls import path, include
from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("search", views.search, name="search"),

    # BOOK
    path("books_add/<int:list_id>-<str:slug>", views.books_add, name="books_add"),
    path("bil_add/<int_list_id>", views.bil_add, name="bil_add"),
    path("bil_edit/<int:bil_id>", views.bil_edit, name="bil_edit"),
    path("bil_delete/<int:bil_id>", views.bil_delete, name="bil_delete"),
    
    # LIST
    path("lists", views.lists, name="lists"),
    path("list_add", views.list_add, name="list_add"),
    path("list_done/<int:list_id>-<str:slug>", views.list_done, name="list_done"),
    path("lists/<int:list_id>-<str:slug>/<int:master_id>", views.list_details, name="list"),
    path("lists/<int:list_id>-<str:slug>", views.list_details, name="list"),
    path("lists/edit/<int:list_id>-<str:slug>", views.list_edit, name="list_edit"),
    path("lists/delete/<int:list_id>", views.list_delete, name="list_delete"),#NO SLUG
    
    # TOPIC
    path("master_add", views.master_add, name="master_add"),
    path("masters", views.masters, name="masters"),
    path("masters/<int:master_id>-<str:slug>", views.master, name="master"),
    path("masters/author_ranking/<int:master_id>-<str:slug>", views.master_author_ranking, name="master_author_ranking"),
    path("masters/lists/<int:master_id>-<str:slug>", views.master_lists, name="master_lists"),
    path("masters/delete/<int:master_id>", views.master_delete, name="master_delete"),#NO SLUG     
    path("masters/edit/<int:master_id>", views.master_edit, name="master_edit"),#NO SLUG
]