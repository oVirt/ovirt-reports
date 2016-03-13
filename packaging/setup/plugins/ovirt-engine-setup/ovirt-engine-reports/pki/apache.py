#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2014-2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""apache PKI plugin."""


import contextlib
import gettext
import os
import time
import urllib2

from otopi import constants as otopicons
from otopi import filetransaction
from otopi import plugin
from otopi import util

from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup import remote_engine
from ovirt_engine_setup.engine_common import constants as oengcommcons
from ovirt_engine_setup.reports import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):
    """apache pki plugin."""

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)
        self._enabled = False
        self._enrolldata = None
        self._need_ca_cert = False
        self._apache_ca_cert = None

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self.environment.setdefault(
            oreportscons.ConfigEnv.PKI_APACHE_CSR_FILENAME,
            None
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        before=(
            oengcommcons.Stages.DIALOG_TITLES_E_PKI,
        ),
        after=(
            oreportscons.Stages.CORE_ENABLE,
            oreportscons.Stages.ENGINE_CORE_ENABLE,
            oengcommcons.Stages.DIALOG_TITLES_S_PKI,
        ),
        condition=lambda self: (
            self.environment[
                oreportscons.CoreEnv.ENABLE
            ] and
            # If on same host as engine, engine setup code creates pki for us
            not self.environment[
                oreportscons.EngineCoreEnv.ENABLE
            ]
        ),
    )
    def _customization(self):
        engine_apache_pki_found = (
            os.path.exists(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_KEY
            ) and os.path.exists(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CA_CERT
            ) and os.path.exists(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CERT
            )
        )

        if not engine_apache_pki_found:
            self._enabled = True
            self._enrolldata = remote_engine.EnrollCert(
                remote_engine=self.environment[
                    osetupcons.CoreEnv.REMOTE_ENGINE
                ],
                engine_fqdn=self.environment[
                    oreportscons.EngineConfigEnv.ENGINE_FQDN
                ],
                base_name=oreportscons.Const.PKI_REPORTS_APACHE_CERT_NAME,
                base_touser=_('Apache'),
                key_file=oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_APACHE_KEY,
                cert_file=oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_APACHE_CERT,
                csr_fname_envkey=(
                    oreportscons.ConfigEnv.PKI_APACHE_CSR_FILENAME
                ),
                engine_ca_cert_file=os.path.join(
                    oreportscons.FileLocations.OVIRT_ENGINE_PKIDIR,
                    'ca.pem'
                ),
                engine_pki_requests_dir=oreportscons.FileLocations.
                OVIRT_ENGINE_PKIREQUESTSDIR,
                engine_pki_certs_dir=oreportscons.FileLocations.
                OVIRT_ENGINE_PKICERTSDIR,
                key_size=self.environment[oreportscons.ConfigEnv.KEY_SIZE],
                url="http://www.ovirt.org/Features/Separate-Reports-Host",
            )
            self._enrolldata.enroll_cert()

            self._need_ca_cert = not os.path.exists(
                oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_APACHE_CA_CERT
            )

        tries_left = 30
        while (
            self._need_ca_cert and
            self._apache_ca_cert is None and
            tries_left > 0
        ):
            remote_engine_host = self.environment[
                oreportscons.EngineConfigEnv.ENGINE_FQDN
            ]

            with contextlib.closing(
                urllib2.urlopen(
                    'http://{engine_fqdn}/ovirt-engine/services/'
                    'pki-resource?resource=ca-certificate&'
                    'format=X509-PEM'.format(
                        engine_fqdn=remote_engine_host
                    )
                )
            ) as urlObj:
                engine_ca_cert = urlObj.read()
                if engine_ca_cert:
                    self._apache_ca_cert = engine_ca_cert
                else:
                    self.logger.error(
                        _(
                            'Failed to get CA Certificate from engine. '
                            'Please check access to the engine and its '
                            'status.'
                        )
                    )
                    time.sleep(10)
                    tries_left -= 1
        if self._need_ca_cert and self._apache_ca_cert is None:
            raise RuntimeError(_('Failed to get CA Certificate from engine'))

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda self: (
            self._enabled
        ),
        after=(
            oreportscons.Stages.CA_AVAILABLE,
            oreportscons.Stages.PKI_MISC,
        ),
    )
    def _misc_pki(self):
        self._enrolldata.add_to_transaction(
            uninstall_group_name='ca_pki_reports',
            uninstall_group_desc='Reports PKI keys',
        )
        uninstall_files = []
        self.environment[
            osetupcons.CoreEnv.REGISTER_UNINSTALL_GROUPS
        ].createGroup(
            group='ca_pki_reports',
            description='Reports PKI keys',
            optional=True,
        ).addFiles(
            group='ca_pki_reports',
            fileList=uninstall_files,
        )
        if not os.path.exists(
            oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CERT
        ):
            os.symlink(
                oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_APACHE_CERT,
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CERT
            )
            uninstall_files.append(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CERT
            )
        if not os.path.exists(
            oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_KEY
        ):
            os.symlink(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_REPORTS_APACHE_KEY,
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_KEY
            )
            uninstall_files.append(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_KEY
            )

        if self._need_ca_cert:
            self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
                filetransaction.FileTransaction(
                    name=oreportscons.FileLocations.
                    OVIRT_ENGINE_PKI_REPORTS_APACHE_CA_CERT,
                    mode=0o600,
                    owner=self.environment[osetupcons.SystemEnv.USER_ENGINE],
                    enforcePermissions=True,
                    content=self._apache_ca_cert,
                    modifiedList=uninstall_files,
                )
            )
            os.symlink(
                oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_APACHE_CA_CERT,
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CA_CERT
            )
            uninstall_files.append(
                oreportscons.FileLocations.OVIRT_ENGINE_PKI_APACHE_CA_CERT
            )

    @plugin.event(
        stage=plugin.Stages.STAGE_CLEANUP,
        condition=lambda self: (
            self._enabled
        ),
    )
    def _cleanup(self):
        self._enrolldata.cleanup()


# vim: expandtab tabstop=4 shiftwidth=4
