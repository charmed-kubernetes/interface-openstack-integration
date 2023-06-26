# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

"""Provide ops charm a means of interacting with the OpenstackIntegration relation."""

from .requires import OpenstackIntegrationRequirer

__all__ = ["OpenstackIntegrationRequirer"]
