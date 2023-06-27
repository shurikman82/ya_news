import pytest

from http import HTTPStatus
from pytest_django.asserts import assertRedirects, assertFormError

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from news.forms import BAD_WORDS, WARNING
from news.models import Comment, News

User = get_user_model()


def test_anonymous_user_cant_create_comment(client, news, form_data):
    url = reverse('news:detail', args=(news.id,))
    # Совершаем запрос от анонимного клиента, в POST-запросе отправляем
    # предварительно подготовленные данные формы с текстом комментария.
    client.post(url, data=form_data)
    # Считаем количество комментариев.
    comments_count = Comment.objects.count()
    # Ожидаем, что комментариев в базе нет - сравниваем с нулём.
    assert comments_count == 0


def test_user_can_create_comment(admin_client, form_data, news):
    # Совершаем запрос через авторизованный клиент.
    url = reverse('news:detail', args=(news.id,))
    response = admin_client.post(url, data=form_data)
    # Проверяем, что редирект привёл к разделу с комментами.
    redirect = f'{url}#comments'
    assert response, redirect
    # Считаем количество комментариев.
    comments_count = Comment.objects.count()
    # Убеждаемся, что есть один комментарий.
    assert comments_count, 1
    # Получаем объект комментария из базы.
    comment = Comment.objects.get()
    # Проверяем, что все атрибуты комментариев совпадают с ожидаемыми.
    assert comment.text, 'Текст комментария'
    assert comment.news, news
    assert comment.author, admin_client


def test_user_cant_use_bad_words(admin_client, news):
    url = reverse('news:detail', args=(news.id,))
    # Формируем данные для отправки формы; текст включает
    # первое слово из списка стоп-слов.
    bad_words_data = {'text': f'Какой-то текст, {BAD_WORDS[0]}, еще текст'}
    # Отправляем запрос через авторизованный клиент.
    response = admin_client.post(url, data=bad_words_data)
    # Проверяем, есть ли в ответе ошибка формы.
    assertFormError(response, form='form', field='text', errors=WARNING)
    # Дополнительно убедимся, что комментарий не был создан.
    comments_count = Comment.objects.count()
    assert comments_count == 0


def test_author_can_delete_comment(author_client, comment, news):
    # От имени автора комментария отправляем DELETE-запрос на удаление.
    url = reverse('news:delete', args=(comment.id,))
    news_url = reverse('news:detail', args=(news.id,))  # Адрес новости.
    url_to_comments = news_url + '#comments'
    response = author_client.delete(url)
    # Проверяем, что редирект привёл к разделу с комментариями.
    # Заодно проверим статус-коды ответов.
    assertRedirects(response, url_to_comments)
    # Считаем количество комментариев в системе.
    comments_count = Comment.objects.count()
    # Ожидаем ноль комментариев в системе.
    assert comments_count == 0


def test_user_cant_delete_comment_of_another_user(admin_client, comment):
    # Выполняем запрос на удаление от пользователя-читателя.
    url = reverse('news:delete', args=(comment.id,))
    response = admin_client.delete(url)
    # Проверяем, что вернулась 404 ошибка.
    assert response.status_code, HTTPStatus.NOT_FOUND
    # Убедимся, что комментарий по-прежнему на месте.
    comments_count = Comment.objects.count()
    assert comments_count == 1


def test_author_can_edit_comment(author_client, comment, news, form_data):
    # Выполняем запрос на редактирование от имени автора комментария.
    url = reverse('news:edit', args=(comment.id,))
    response = author_client.post(url, data=form_data)
    # Проверяем, что сработал редирект.
    news_url = reverse('news:detail', args=(news.id,))
    url_to_comments = news_url + '#comments'
    assertRedirects(response, url_to_comments)
    # Обновляем объект комментария.
    comment.refresh_from_db()
    # Проверяем, что текст комментария соответствует обновленному.
    assert comment.text, 'Новый текст'


def test_user_cant_edit_comment_of_another_user(admin_client, comment, form_data):
    # Выполняем запрос на редактирование от имени другого пользователя.
    url = reverse('news:edit', args=(comment.id,))
    response = admin_client.post(url, data=form_data)
    # Проверяем, что вернулась 404 ошибка.
    assert response.status_code, HTTPStatus.NOT_FOUND
    # Обновляем объект комментария.
    comment.refresh_from_db()
    # Проверяем, что текст остался тем же, что и был.
    assert comment.text, 'Текст комментария'
