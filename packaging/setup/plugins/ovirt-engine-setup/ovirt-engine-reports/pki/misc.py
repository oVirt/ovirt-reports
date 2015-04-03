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


"""misc PKI plugin."""


import gettext
import os


from otopi import plugin
from otopi import util


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup import util as osetuputil
from ovirt_engine_setup.engine_common import constants as oengcommcons
from ovirt_engine_setup.reports import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):
    """misc pki plugin."""

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    def _install_d(self, dirname, mode=None, uid=-1, gid=-1):
        if not os.path.exists(dirname):
            os.makedirs(dirname)
            if mode is not None:
                os.chmod(dirname, mode)
            os.chown(dirname, uid, gid)

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self.environment.setdefault(
            oreportscons.ConfigEnv.KEY_SIZE,
            oreportscons.Defaults.DEFAULT_KEY_SIZE
        )
        self._enabled = False

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        after=(
            oreportscons.Stages.CORE_ENABLE,
            oreportscons.Stages.ENGINE_CORE_ENABLE,
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

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        name=oreportscons.Stages.PKI_MISC,
        condition=lambda self: (
            self._enabled
        ),
        after=(
            oreportscons.Stages.CA_AVAILABLE,
        ),
    )
    def _misc_pki(self):
        ovirtuid = osetuputil.getUid(
            self.environment[osetupcons.SystemEnv.USER_ENGINE]
        )
        ovirtgid = osetuputil.getGid(
            self.environment[osetupcons.SystemEnv.GROUP_ENGINE]
        )
        rootuid = osetuputil.getGid(
            self.environment[oengcommcons.SystemEnv.USER_ROOT]
        )
        self._install_d(
            dirname=oreportscons.FileLocations.OVIRT_ENGINE_PKIDIR,
            mode=0o755,
            uid=ovirtuid,
            gid=ovirtgid,
        )
        self._install_d(
            dirname=oreportscons.FileLocations.OVIRT_ENGINE_PKIKEYSDIR,
            mode=0o755,
            uid=rootuid,
            gid=-1,
        )
        self._install_d(
            dirname=oreportscons.FileLocations.OVIRT_ENGINE_PKICERTSDIR,
            mode=0o755,
            uid=ovirtuid,
            gid=ovirtgid,
        )


# vim: expandtab tabstop=4 shiftwidth=4
