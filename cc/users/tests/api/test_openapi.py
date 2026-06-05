from http import HTTPStatus

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_api_docs_accessible_by_admin(admin_client) -> None:
    url = reverse("api-docs")
    response = admin_client.get(url)
    assert response.status_code == HTTPStatus.OK


def test_api_docs_not_accessible_by_anonymous_users(client) -> None:
    url = reverse("api-docs")
    response = client.get(url)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_api_schema_generated_successfully(admin_client) -> None:
    url = reverse("api-schema")
    response = admin_client.get(url)
    assert response.status_code == HTTPStatus.OK
