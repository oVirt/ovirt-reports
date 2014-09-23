#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2014 Red Hat, Inc.
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


"""jboss PKI plugin."""


import os


import gettext
_ = lambda m: gettext.dgettext(message=m, domain='ovirt-engine-reports')


from otopi import util
from otopi import plugin


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup import remote_engine
from ovirt_engine_setup.engine_common import constants as oengcommcons
from ovirt_engine_setup.reports import constants as oreportscons


@util.export
class Plugin(plugin.PluginBase):
    """jboss pki plugin."""

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)
        self._enabled = False
        self._enrolldata = None

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self.environment.setdefault(
            oreportscons.ConfigEnv.PKI_JBOSS_CSR_FILENAME,
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
            # If on same host as engine, engine setup creates pki for us
            not self.environment[
                oreportscons.EngineCoreEnv.ENABLE
            ]
        ),
    )
    def _customization(self):
        self._enabled = True
        self._enrolldata = remote_engine.EnrollCert(
            remote_engine=self.environment[osetupcons.CoreEnv.REMOTE_ENGINE],
            engine_fqdn=self.environment[
                oreportscons.EngineConfigEnv.ENGINE_FQDN
            ],
            base_name=oreportscons.Const.PKI_REPORTS_JBOSS_CERT_NAME,
            base_touser=_('Reports'),
            key_file=oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_JBOSS_KEY,
            cert_file=oreportscons.FileLocations.
                OVIRT_ENGINE_PKI_REPORTS_JBOSS_CERT,
            csr_fname_envkey=oreportscons.ConfigEnv.PKI_JBOSS_CSR_FILENAME,
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

    @plugin.event(
        stage=plugin.Stages.STAGE_CLEANUP,
        condition=lambda self: (
            self._enabled
        ),
    )
    def _cleanup(self):
        self._enrolldata.cleanup()


# vim: expandtab tabstop=4 shiftwidth=4
