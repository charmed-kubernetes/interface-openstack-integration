# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""pydantic model of the databag read by the requires side."""

import base64
import binascii
import configparser
import contextlib
import io
from typing import Optional

from pydantic import BaseModel, Json, SecretStr, validator


class Data(BaseModel):
    """Databag for information shared over the relation."""

    # Required config
    auth_url: Json[str]
    password: Json[SecretStr]
    project_domain_name: Json[str]
    project_name: Json[str]
    region: Json[str]
    username: Json[str]
    user_domain_name: Json[str]

    # Optional config
    bs_version: Json[Optional[str]]
    endpoint_tls_ca: Json[Optional[str]]
    floating_network_id: Json[Optional[str]]
    has_octavia: Json[Optional[bool]]
    ignore_volume_az: Json[Optional[bool]]
    internal_lb: Json[Optional[bool]]
    lb_enabled: Json[Optional[bool]]
    lb_method: Json[Optional[str]]
    manage_security_groups: Json[Optional[bool]]
    subnet_id: Json[Optional[str]]
    trust_device_path: Json[Optional[bool]]
    version: Json[Optional[int]]

    @validator("endpoint_tls_ca")
    def must_be_b64_cert(cls, s: Json[str]):
        """Validate endpoint_tls_ca is base64 encoded str."""
        try:
            base64.b64decode(s, validate=True)
        except binascii.Error:
            raise ValueError("Couldn't find base64 data")
        return s

    @property
    def cloud_config(self) -> str:  # noqa: C901
        """Render as an openstack cloud config ini."""
        config = configparser.ConfigParser()
        config["Global"] = {
            "auth-url": self.auth_url,
            "region": self.region,
            "username": self.username,
            "password": self.password.get_secret_value(),
            "tenant-name": self.project_name,
            "domain-name": self.user_domain_name,
            "tenant-domain-name": self.project_domain_name,
        }
        if self.endpoint_tls_ca:
            config["Global"]["ca-file"] = "/etc/config/endpoint-ca.cert"

        config["LoadBalancer"] = {}
        if not self.lb_enabled:
            config["LoadBalancer"]["enabled"] = "false"
        if self.has_octavia in (True, None):
            # Newer integrator charm will detect whether underlying OpenStack has
            # Octavia enabled so we can set this intelligently. If we're still
            # related to an older integrator, though, default to assuming Octavia
            # is available.
            config["LoadBalancer"]["use-octavia"] = "true"
        else:
            config["LoadBalancer"]["use-octavia"] = "false"
            config["LoadBalancer"]["lb-provider"] = "haproxy"
        if _s := self.subnet_id:
            config["LoadBalancer"]["subnet-id"] = _s
        if _s := self.floating_network_id:
            config["LoadBalancer"]["floating-network-id"] = _s
        if _s := self.lb_method:
            config["LoadBalancer"]["lb-method"] = _s
        if self.internal_lb:
            config["LoadBalancer"]["internal-lb"] = "true"
        if self.manage_security_groups:
            config["LoadBalancer"]["manage-security-groups"] = "true"

        config["BlockStorage"] = {}
        if _os := self.bs_version:
            config["BlockStorage"]["bs-version"] = _os
        if self.trust_device_path:
            config["BlockStorage"]["trust-device-path"] = "true"
        if self.ignore_volume_az:
            config["BlockStorage"]["ignore-volume-az"] = "true"

        with contextlib.closing(io.StringIO()) as sio:
            config.write(sio)
            output_text = sio.getvalue()

        return output_text
