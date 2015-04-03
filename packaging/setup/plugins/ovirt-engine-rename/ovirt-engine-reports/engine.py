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


"""Engine plugin."""


import gettext
import urlparse


from otopi import constants as otopicons
from otopi import filetransaction
from otopi import plugin
from otopi import util


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup.reports import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):
    """Engine plugin."""

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        condition=lambda self: (
            self.environment[oreportscons.EngineCoreEnv.ENABLE]
        ),
    )
    def _misc(self):
        uninstall_files = []
        self.environment[
            osetupcons.CoreEnv.REGISTER_UNINSTALL_GROUPS
        ].addFiles(
            group='ovirt_reports_files',
            fileList=uninstall_files,
        )
        config = (
            oreportscons.EngineFileLocations.
            OVIRT_ENGINE_SERVICE_CONFIG_REPORTS
        )
        with open(config, 'r') as f:
            content = []
            key = 'ENGINE_REPORTS_BASE_URL'
            for line in f:
                line = line.rstrip('\n')
                if line.startswith('%s=' % key):
                    u = urlparse.urlparse(line[len('%s=' % key):])
                    ulist = list(u)
                    ulist[1] = self.environment[osetupcons.RenameEnv.FQDN] + (
                        ':' + str(u.port) if u.port
                        else ''
                    )
                    line = '{key}={url}'.format(
                        key=key,
                        url=urlparse.urlunparse(ulist),
                    )
                content.append(line)

        self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
            filetransaction.FileTransaction(
                name=config,
                content=content,
                modifiedList=uninstall_files,
            )
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_CLOSEUP,
        condition=lambda self: not (
            self.environment[oreportscons.EngineCoreEnv.ENABLE]
        ),
        before=(
            osetupcons.Stages.DIALOG_TITLES_E_SUMMARY,
        ),
        after=(
            osetupcons.Stages.DIALOG_TITLES_S_SUMMARY,
        ),
    )
    def _closeup(self):
        self.dialog.note(
            text=_(
                "\nTo update the engine with the new Reports host name, "
                "please edit the file '{name}' on the engine host, replace "
                "there the old name with the new name, and restart the engine "
                "service by running there:\n"
                "# service ovirt-engine restart\n"
            ).format(
                name=(
                    oreportscons.EngineFileLocations.
                    OVIRT_ENGINE_SERVICE_CONFIG_REPORTS
                ),
            ),
        )


# vim: expandtab tabstop=4 shiftwidth=4
