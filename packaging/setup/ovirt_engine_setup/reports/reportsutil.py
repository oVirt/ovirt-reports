#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2013-2015 Red Hat, Inc.
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


"""Utils."""


import atexit
import gettext
import os
import re
import shutil
import tempfile


import libxml2


from otopi import base
from otopi import util


from ovirt_engine_setup.engine_common \
    import constants as oengcommcons
from . import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


class XMLDoc(base.Base):

    @property
    def document(self):
        return self._doc

    @property
    def xpath(self):
        return self._ctx

    def __init__(self, f):
        super(XMLDoc, self).__init__()
        self._file = f
        self._doc = None
        self._ctx = None

    def __enter__(self):
        self._doc = libxml2.parseFile(self._file)
        self._ctx = self._doc.xpathNewContext()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_type:
            with open(self._file, 'w') as f:
                f.write(
                    self._doc.serialize(
                        'UTF-8',
                        libxml2.XML_SAVE_FORMAT,
                    )
                )
            os.chmod(self._file, 0o644)

        if self._doc:
            self._doc.freeDoc()
            self._doc = None
        if self._ctx:
            self._ctx.xpathFreeContext()
            self._ctx = None

    def setNodesContent(self, path, content):
        for node in self.xpath.xpathEval(path):
            node.setContent(content)


@util.export
class JasperUtil(base.Base):

    @property
    def environment(self):
        return self._plugin.environment

    def __init__(self, plugin):
        super(JasperUtil, self).__init__()
        self._plugin = plugin
        self._temproot = tempfile.mkdtemp()
        atexit.register(shutil.rmtree, self._temproot)
        self._javatmp = os.path.join(self._temproot, 'tmp')
        os.mkdir(self._javatmp)

    _IGNORED_ERRORS = (
        '.*This normal shutdown operation.*',
    )

    _RE_IGNORED_ERRORS = re.compile(
        pattern='|'.join(_IGNORED_ERRORS),
    )

    def _execute(self, *eargs, **kwargs):
        rc, stdout, stderr = self._plugin.execute(*eargs, **kwargs)

        if stderr:
            errors = [
                l for l in stderr
                if l and not self._RE_IGNORED_ERRORS.match(l)
            ]

        if rc != 0 or errors:
            self._plugin.logger.error('JasperUtil execute failed')
            raise RuntimeError('JasperUtil execute failed')

    def jsexport(self, what, args):
        dest = os.path.join(
            self._temproot,
            what,
        )
        self._execute(
            args=(
                './js-export.sh',
                '--output-dir', dest,
            ) + args,
            cwd=os.path.join(
                self.environment[
                    oreportscons.ConfigEnv.JASPER_HOME
                ],
                'buildomatic',
            ),
            envAppend={
                'JAVA_HOME': self.environment[
                    oengcommcons.ConfigEnv.JAVA_HOME
                ],
                'JAVA_OPTS': '-Djava.io.tmpdir=%s' % self._javatmp,
                'ADDITIONAL_CONFIG_DIR': (
                    oreportscons.FileLocations.
                    OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG
                ),
                'ANT_OPTS': '-DmasterPropsSource={master}'.format(
                    master=(
                        oreportscons.FileLocations.
                        OVIRT_ENGINE_REPORTS_BUILDOMATIC_DBPROP
                    ),
                ),
            },
        )
        return dest

    def jsimport(self, src):
        self._execute(
            args=(
                './js-import.sh',
                '--input-dir', src,
                '--update',
            ),
            cwd=os.path.join(
                self.environment[
                    oreportscons.ConfigEnv.JASPER_HOME
                ],
                'buildomatic',
            ),
            envAppend={
                'JAVA_HOME': self.environment[
                    oengcommcons.ConfigEnv.JAVA_HOME
                ],
                'JAVA_OPTS': '-Djava.io.tmpdir=%s' % self._javatmp,
                'ADDITIONAL_CONFIG_DIR': (
                    oreportscons.FileLocations.
                    OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG
                ),
                'ANT_OPTS': '-DmasterPropsSource={master}'.format(
                    master=(
                        oreportscons.FileLocations.
                        OVIRT_ENGINE_REPORTS_BUILDOMATIC_DBPROP
                    ),
                ),
            },
        )


# vim: expandtab tabstop=4 shiftwidth=4
