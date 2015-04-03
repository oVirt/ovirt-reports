#!/usr/bin/python

# Copyright 2014-2015 Red Hat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import gettext
import os
import re
import shlex
import sys


from Cheetah.Template import Template


import config


from ovirt_engine import configfile
from ovirt_engine import java
from ovirt_engine import service


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


class Daemon(service.Daemon):

    def __init__(self):
        super(Daemon, self).__init__()
        self._tempDir = None
        self._jbossRuntime = None
        self._defaults = os.path.abspath(
            os.path.join(
                os.path.dirname(sys.argv[0]),
                'ovirt-engine-reportsd.conf',
            )
        )

    def _processTemplate(self, template, dir, mode=None):
        out = os.path.join(
            dir,
            re.sub('\.in$', '', os.path.basename(template)),
        )
        with open(out, 'w') as f:
            if mode is not None:
                os.chmod(out, mode)
            f.write(
                '%s' % (
                    Template(
                        file=template,
                        searchList=[
                            self._config,
                            {
                                'jboss_runtime': self._jbossRuntime.directory,
                            },
                        ],
                    )
                ),
            )
        return out

    def _linkModules(self, directory, modulePath):
        """
        Link all the JBoss modules into a temporary directory.
        This required because jboss tries to automatically update
        indexes based on timestamp even if there is no permission to do so.
        """

        modifiedModulePath = []
        for index, element in enumerate(modulePath.split(':')):
            modulesTmpDir = os.path.join(
                directory,
                '%02d-%s' % (
                    index,
                    '-'.join(element.split(os.sep)[-2:]),
                ),
            )
            modifiedModulePath.append(modulesTmpDir)

            # For each directory in the modules directory create the
            # same in the temporary directory and populate with symlinks
            # pointing to the original files (excluding indexes):
            for parentDir, childrenDirs, childrenFiles in os.walk(element):
                parentTmpDir = os.path.join(
                    modulesTmpDir,
                    os.path.relpath(
                        parentDir,
                        element
                    ),
                )
                if not os.path.exists(parentTmpDir):
                    os.makedirs(parentTmpDir)
                for childFile in childrenFiles:
                    if childFile.endswith('.index'):
                        continue
                    os.symlink(
                        os.path.join(parentDir, childFile),
                        os.path.join(parentTmpDir, childFile)
                    )

        return ':'.join(modifiedModulePath)

    def _checkInstallation(
        self,
        pidfile,
        jbossModulesJar,
    ):
        # Check the required JBoss directories and files:
        self.check(
            name=self._config.get('JBOSS_HOME'),
            directory=True,
        )
        self.check(
            name=jbossModulesJar,
        )

        # Check the required directories and files:
        self.check(
            os.path.join(
                self._config.get('PKG_DATA_DIR'),
                'services',
            ),
            directory=True,
        )
        self.check(
            self._config.get('PKG_TMP_DIR'),
            directory=True,
            writable=True,
            mustExist=False,
        )
        self.check(
            self._config.get('PKG_LOG_DIR'),
            directory=True,
            writable=True,
        )
        for log in ('reports.log', 'console.log', 'server.log'):
            self.check(
                name=os.path.join(self._config.get("PKG_LOG_DIR"), log),
                mustExist=False,
                writable=True,
            )
        if pidfile is not None:
            self.check(
                name=pidfile,
                writable=True,
                mustExist=False,
            )

    def _setupApps(self):

        deploymentsDir = os.path.join(
            self._jbossRuntime.directory,
            'deployments',
        )
        os.mkdir(deploymentsDir)

        # The list of applications to be deployed:
        for AppDir in shlex.split(self._config.get('REPORTS_APPS')):
            self.logger.debug('Deploying: %s', AppDir)
            if not os.path.isabs(AppDir):
                AppDir = os.path.join(
                    self._config.get('PKG_DATA_DIR'),
                    AppDir,
                )
            if not os.path.exists(AppDir):
                self.logger.warning(
                    _(
                        "Application directory '{directory}' "
                        "does not exist, it will be ignored"
                    ).format(
                        directory=AppDir,
                    ),
                )
                continue

            AppLink = os.path.join(
                deploymentsDir,
                os.path.basename(AppDir),
            )
            os.symlink(AppDir, AppLink)
            with open('%s.dodeploy' % AppLink, 'w'):
                pass

    def daemonSetup(self):

        if os.geteuid() == 0:
            raise RuntimeError(
                _('This service cannot be executed as root')
            )

        if not os.path.exists(self._defaults):
            raise RuntimeError(
                _(
                    "The configuration defaults file '{file}' "
                    "required but missing"
                ).format(
                    file=self._defaults,
                )
            )

        self._config = configfile.ConfigFile(
            (
                self._defaults,
                config.SERVICE_VARS,
            ),
        )

        #
        # the earliest so we can abort early.
        #
        self._executable = os.path.join(
            java.Java().getJavaHome(),
            'bin',
            'java',
        )

        jbossModulesJar = os.path.join(
            self._config.get('JBOSS_HOME'),
            'jboss-modules.jar',
        )

        self._checkInstallation(
            pidfile=self.pidfile,
            jbossModulesJar=jbossModulesJar,
        )

        self._tempDir = service.TempDir(self._config.get('PKG_TMP_DIR'))
        self._tempDir.create()

        self._jbossRuntime = service.TempDir(self._config.get('JBOSS_RUNTIME'))
        self._jbossRuntime.create()

        self._setupApps()

        jbossTempDir = os.path.join(
            self._jbossRuntime.directory,
            'tmp',
        )

        jbossConfigDir = os.path.join(
            self._jbossRuntime.directory,
            'config',
        )

        javaModulePath = self._linkModules(
            os.path.join(
                self._jbossRuntime.directory,
                'modules',
            ),
            '%s:%s' % (
                self._config.get('JAVA_MODULEPATH'),
                os.path.join(
                    self._config.get('JBOSS_HOME'),
                    'modules',
                ),
            ),
        )

        os.mkdir(jbossTempDir)
        os.mkdir(jbossConfigDir)
        os.chmod(jbossConfigDir, 0o700)

        jbossBootLoggingFile = self._processTemplate(
            template=os.path.join(
                os.path.dirname(sys.argv[0]),
                'ovirt-engine-reportsd-logging.properties.in'
            ),
            dir=jbossConfigDir,
        )

        jbossConfigFile = self._processTemplate(
            template=os.path.join(
                os.path.dirname(sys.argv[0]),
                'ovirt-engine-reportsd.xml.in',
            ),
            dir=jbossConfigDir,
            mode=0o600,
        )

        # We start with an empty list of arguments:
        self._serviceArgs = []

        # Add arguments for the java virtual machine:
        self._serviceArgs.extend([
            # The name or the process, as displayed by ps:
            'ovirt-engine-reportsd',

            # Virtual machine options:
            '-server',
            '-XX:+TieredCompilation',
            '-Xms%s' % self._config.get('HEAP_MIN'),
            '-Xmx%s' % self._config.get('HEAP_MAX'),
            '-XX:PermSize=%s' % self._config.get('PERM_MIN'),
            '-XX:MaxPermSize=%s' % self._config.get('PERM_MAX'),
            '-Djava.net.preferIPv4Stack=true',
            '-Dsun.rmi.dgc.client.gcInterval=3600000',
            '-Dsun.rmi.dgc.server.gcInterval=3600000',
            '-Djava.awt.headless=true',
        ])

        # Add extra system properties provided in the configuration:
        for serviceProperty in shlex.split(
            self._config.get('REPORTS_PROPERTIES')
        ):
            if not serviceProperty.startswith('-D'):
                serviceProperty = '-D' + serviceProperty
            self._serviceArgs.append(serviceProperty)

        # Add extra jvm arguments provided in the configuration:
        for arg in shlex.split(self._config.get('JVM_ARGS')):
            self._serviceArgs.append(arg)

        # Add arguments for remote debugging of the java virtual machine:
        debugAddress = self._config.get('DEBUG_ADDRESS')
        if debugAddress:
            self._serviceArgs.append(
                (
                    '-Xrunjdwp:transport=dt_socket,address=%s,'
                    'server=y,suspend=n'
                ) % (
                    debugAddress
                )
            )

        # Enable verbose garbage collection if required:
        if self._config.getboolean('VERBOSE_GC'):
            self._serviceArgs.extend([
                '-verbose:gc',
                '-XX:+PrintGCTimeStamps',
                '-XX:+PrintGCDetails',
            ])

        # Add arguments for JBoss:
        self._serviceArgs.extend([
            '-Djava.util.logging.manager=org.jboss.logmanager',
            '-Dlogging.configuration=file://%s' % jbossBootLoggingFile,
            '-Dorg.jboss.resolver.warning=true',
            '-Djboss.modules.system.pkgs=org.jboss.byteman',
            '-Djboss.modules.write-indexes=false',
            '-Djboss.server.default.config=ovirt-engine-reportsd',
            '-Djboss.home.dir=%s' % self._config.get(
                'JBOSS_HOME'
            ),
            '-Djboss.server.base.dir=%s' % self._config.get(
                'PKG_DATA_DIR'
            ),
            '-Djboss.server.data.dir=%s' % self._config.get(
                'PKG_STATE_DIR'
            ),
            '-Djboss.server.log.dir=%s' % self._config.get(
                'PKG_LOG_DIR'
            ),
            '-Djboss.server.config.dir=%s' % jbossConfigDir,
            '-Djboss.server.temp.dir=%s' % jbossTempDir,
            '-Djboss.controller.temp.dir=%s' % jbossTempDir,
            '-jar', jbossModulesJar,
            '-mp', javaModulePath,
            '-jaxpmodule', 'javax.xml.jaxp-provider',
            'org.jboss.as.standalone',
            '-c', os.path.basename(jbossConfigFile),
        ])

        self._serviceEnv = os.environ.copy()
        self._serviceEnv.update({
            'PATH': (
                '/usr/local/sbin:/usr/local/bin:'
                '/usr/sbin:/usr/bin:/sbin:/bin'
            ),
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8',
            'SERVICE_DEFAULTS': self._defaults,
            'SERVICE_VARS': config.SERVICE_VARS,
            'PKG_LOG_DIR': self._config.get('PKG_LOG_DIR'),
            'PKG_TMP_DIR': self._tempDir.directory,
            'PKG_DATA_DIR': self._config.get('PKG_DATA_DIR'),
            'PKG_STATE_DIR': self._config.get('PKG_STATE_DIR'),
        })

    def daemonStdHandles(self):
        consoleLog = open(
            os.path.join(
                self._config.get('PKG_LOG_DIR'),
                'console.log'
            ),
            'w+',
        )
        return (consoleLog, consoleLog)

    def daemonContext(self):
        try:
            #
            # create mark file to be used by notifier service
            #
            with open(self._config.get('SERVICE_UP_MARK'), 'w') as f:
                f.write('%s\n' % os.getpid())

            self.daemonAsExternalProcess(
                executable=self._executable,
                args=self._serviceArgs,
                env=self._serviceEnv,
                stopTime=self._config.getinteger(
                    'STOP_TIME'
                ),
                stopInterval=self._config.getinteger(
                    'STOP_INTERVAL'
                ),
            )

            raise self.TerminateException()

        except self.TerminateException:
            if os.path.exists(self._config.get('SERVICE_UP_MARK')):
                os.remove(self._config.get('SERVICE_UP_MARK'))

    def daemonCleanup(self):
        if self._tempDir:
            self._tempDir.destroy()
        if self._jbossRuntime:
            self._jbossRuntime.destroy()


if __name__ == '__main__':
    service.setupLogger()
    d = Daemon()
    d.run()


# vim: expandtab tabstop=4 shiftwidth=4
