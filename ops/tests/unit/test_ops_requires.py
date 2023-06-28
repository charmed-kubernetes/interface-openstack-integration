# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
import base64
import unittest.mock as mock
from pathlib import Path

import pytest
import yaml
from ops.charm import CharmBase, RelationBrokenEvent

from ops.interface_openstack_integration import OpenstackIntegrationRequirer


@pytest.fixture(scope="function")
def requirer():
    mock_charm = mock.MagicMock(auto_spec=CharmBase)
    mock_charm.framework.model.unit.name = "test/0"
    yield OpenstackIntegrationRequirer(mock_charm)


@pytest.fixture()
def relation_data():
    yield yaml.safe_load(Path("tests/data/openstack_integration_data.yaml").open())


@pytest.mark.parametrize(
    "event_type", [None, RelationBrokenEvent], ids=["unrelated", "dropped relation"]
)
def test_is_ready_no_relation(requirer, event_type):
    with mock.patch.object(
        OpenstackIntegrationRequirer, "relation", new_callable=mock.PropertyMock
    ) as mock_prop:
        relation = mock_prop.return_value
        relation.__bool__.return_value = event_type is not None
        relation.units = []
        event = mock.MagicMock(spec=event_type)
        event.relation = relation
        assert requirer.is_ready is False
        assert "Missing" in requirer.evaluate_relation(event)
        assert requirer.cloud_conf is None
        assert requirer.endpoint_tls_ca is None


def test_is_ready_invalid_data(requirer, relation_data):
    relation_data["version"] = 123
    with mock.patch.object(
        OpenstackIntegrationRequirer, "relation", new_callable=mock.PropertyMock
    ) as mock_prop:
        relation = mock_prop.return_value
        relation.units = ["remote/0"]
        relation.data = {"remote/0": relation_data}
        assert requirer.is_ready is False


def test_is_ready_success(requirer, relation_data):
    with mock.patch.object(
        OpenstackIntegrationRequirer, "relation", new_callable=mock.PropertyMock
    ) as mock_prop:
        relation = mock_prop.return_value
        relation.units = ["remote/0"]
        relation.data = {"remote/0": relation_data}
        assert requirer.is_ready is True


def test_create_config_ini(requirer, relation_data, tmpdir):
    with mock.patch.object(
        OpenstackIntegrationRequirer, "relation", new_callable=mock.PropertyMock
    ) as mock_prop:
        relation = mock_prop.return_value
        relation.units = ["remote/0"]
        relation.data = {"remote/0": relation_data}

        expected = Path("tests/data/cloud_conf.ini").read_text()
        assert requirer.cloud_conf == expected
        assert requirer.cloud_conf_b64 == base64.b64encode(expected.encode())
