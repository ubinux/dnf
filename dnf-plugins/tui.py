# tui.py
# Tgui CLI command.
#
# Copyright (C) 2018 FUJITSU LIMITED
#
from __future__ import absolute_import
from __future__ import unicode_literals
from dnf.cli import commands
from dnf.cli.option_parser import OptionParser
from dnf.i18n import _
from itertools import chain
import dnf.subject

import dnf.exceptions
import hawkey
import logging

from .window import *
from .utils import *
import sys, os, copy, textwrap, snack, string, time, re, shutil
from snack import *

import dnf
import dnf.cli.demand
import dnf.cli.option_parser
import dnf.cli.commands.shell
import dnf.conf
from dnf.cli.option_parser import OptionParser
import dnf.conf.substitutions
import dnf.const
import dnf.exceptions
import dnf.cli.format
import dnf.logging
import dnf.plugin
import dnf.persistor
import dnf.rpm
import dnf.util
import dnf.cli.utils
import dnf.yum.misc
from subprocess import call

_TXT_ROOT_TITLE = "Package Installer"

Install_actions = [("Install", "Choose it to install packages."), \
                   ("Remove", "Choose it to remove packages"), \
                   ("Upgrade", "Choose it to upgrade packages"), \
                   ("Create binary package archives(rpm)", "Choose it to create package archive"), \
                   ("Create a source archive(src.rpm)", "Choose it to create source archive"), \
                   ("Create an spdx archive(spdx)", "Choose it to create SPDX archive"), \
                   ("Create archive(rpm, src.rpm and spdx files)", "Choose it to create all archive") \
                  ]

Custom_actions = [("New", "Install without config file."), \
                  ("Load package file", "Load config file")
                  ]

ACTION_INSTALL     = 0
ACTION_REMOVE      = 1
ACTION_UPGRADE     = 2
ACTION_GET_PKG     = 3
ACTION_GET_SOURCE  = 4
ACTION_GET_SPDX    = 5
ACTION_GET_ALL     = 6
GROUP_INSTALL      = 7

NEW_INSTALL        = 0
RECORD_INSTALL     = 1
SAMPLE_INSTALL     = 2

CONFIRM_EXIT       = 0
CONFIRM_INSTALL    = 1
CONFIRM_LICENSE    = 2
CONFIRM_REMOVE     = 3
CONFIRM_UPGRADE    = 4
CONFIRM_GET_PKG    = 5
CONFIRM_GET_SOURCE = 6
CONFIRM_GET_SPDX   = 7
CONFIRM_GET_ALL    = 8

ATTENTON_NONE           = 0
ATTENTON_HAVE_UPGRADE   = 1
ATTENTON_NONE_UPGRADE   = 2

if "OECORE_NATIVE_SYSROOT" in os.environ:
    NATIVE_SYSROOT = os.environ["OECORE_NATIVE_SYSROOT"]
else:
    NATIVE_SYSROOT = "/opt/poky/2.5/sysroots/x86_64-pokysdk-linux"
SAMPLE = NATIVE_SYSROOT + "/usr/share/dnf"

logger = logging.getLogger('dnf')

@dnf.plugin.register_command
class TuiCommand(commands.Command):
    """A class containing methods needed by the cli to execute the
    tui command.
    """

    aliases = ('tui',)
    summary = _('Enter tui interface.')

    def __init__(self, cli=None):
        cli = cli or dnf.cli.Cli()
        super(TuiCommand, self).__init__(cli=cli)
        self.screen = None
        self.no_gpl3 = False
        self.install_type = ACTION_INSTALL

        self.pkgnarrow = 'all'
        self.patterns = None
        self.installed_available = False
        self.reponame = None
        self.CONFIG_FILE = ".config"
        self.grps = []
        self.group_flag = False
        self.group_botton = False
        self.SAVE = True

    @staticmethod
    def set_argparser(parser):
        parser.add_argument("--init", dest="with_init",
                          action="store_true", default=None,
                          help=_("Init the dnf environment for toolchain"))
        parser.add_argument("--call", dest="with_call",
                          action="store_true", default=None,
                          help=_("Call the dnf tui for toolchain"))

    def pre_configure(self):
        if self.opts.with_init:
            pass
        else:
        #Reload the conf and args
            env_path = os.getcwd() + "/.env-dnf"
            if os.path.exists(env_path):
                self.read_environ(env_path)

                install_root_from_env = os.environ.get('HIDDEN_ROOTFS')
                self.opts.installroot = install_root_from_env

                self.opts.logdir = os.path.split(install_root_from_env)[0]

    def configure(self):
        self.cli.demands = dnf.cli.commands.shell.ShellDemandSheet()
        demands = self.cli.demands
        demands.root_user = False
      

    def run(self, command=None, argv=None):
        if self.opts.with_init:
            plugin_dir = os.path.split(__file__)[0]
            os.system("%s/dnf-host init" %plugin_dir)
            sys.exit(0)

        if self.opts.installroot:  #if used in toolchain
            if self.opts.with_call:
                logger.debug("Enter tui interface.")
                self.PKGINSTDispMain()
            else:
                exit_code = call(["dnf", "tui", "--call", "--installroot={}".format(
                                  self.opts.installroot), "--setopt=logdir={}".format(
                                  self.opts.logdir), "--releasever=None"])
                if exit_code != 0:
                    raise dnf.exceptions.Error(_("Failed to call dnf tui"))
        else:
            logger.debug("Enter tui interface.")
            self.PKGINSTDispMain()

    def read_environ(self, file):
        try:
            with open(file, 'r') as fd:
                lines = fd.readlines()
                for line in lines:
                    #if "PSEUDO" in line:
                    env = line.rstrip().split('=', 1)
                    os.environ[env[0]]=env[1]
        except IOError:
            logger.info(_('Error: Cannot open %s for reading'), self.base.output.term.bold(file))
            sys.exit(1)

    def run_dnf_command(self, s_line):
        """Execute the subcommand you put in.
        """
        opts = self.cli.optparser.parse_main_args(s_line)
        cmd_cls = self.cli.cli_commands.get(opts.command)
        cmd = cmd_cls(self)
        try:
            opts = self.cli.optparser.parse_command_args(cmd, s_line)
            cmd.cli = self.cli
            cmd.cli.demands = copy.deepcopy(self.cli.demands)
            cmd.configure()
            cmd.run()
        except:
            pass

    def PKG_filter(self, packages):
        strings_pattern_end = ('-dev', '-doc', '-dbg', '-staticdev', '-ptest')
        notype_pkgs = packages
        for pkg in packages:
            if "-locale-" in pkg.name:
                notype_pkgs.remove(pkg)
            elif "-localedata-" in pkg.name:
                notype_pkgs.remove(pkg)
            elif pkg.name.endswith(strings_pattern_end):
                notype_pkgs.remove(pkg)
        return notype_pkgs

    def GET_SOURCE_or_SPDX(self, selected_pkgs):
        if self.screen != None:
            StopHotkeyScreen(self.screen)
            self.screen = None
        notype_pkgs = self.PKG_filter(selected_pkgs)
        if self.install_type == ACTION_GET_SOURCE:
            srcdir_path = self.base.conf.srpm_repodir
            destdir_path = self.base.conf.srpm_download
            fetchSPDXorSRPM('srpm', notype_pkgs, srcdir_path, destdir_path)
        elif self.install_type == ACTION_GET_SPDX:
            srcdir_path = self.base.conf.spdx_repodir
            destdir_path = self.base.conf.spdx_download
            fetchSPDXorSRPM('spdx', notype_pkgs, srcdir_path, destdir_path)

    def GET_RKG(self, selected_pkgs):
        if self.screen != None:
            StopHotkeyScreen(self.screen)
            self.screen = None
        srcdir_path = self.base.conf.rpm_repodir
        destdir_path = self.base.conf.rpm_download
        fetchSPDXorSRPM('rpm', selected_pkgs, srcdir_path, destdir_path)

    def GET_ALL(self, selected_pkgs):
        if self.screen != None:
            StopHotkeyScreen(self.screen)
            self.screen = None
        fetchSPDXorSRPM('rpm', selected_pkgs, 
                    self.base.conf.rpm_repodir, self.base.conf.rpm_download)
        notype_pkgs = self.PKG_filter(selected_pkgs)
        fetchSPDXorSRPM('srpm', notype_pkgs, 
                    self.base.conf.srpm_repodir, self.base.conf.srpm_download)
        fetchSPDXorSRPM('spdx', notype_pkgs, 
                    self.base.conf.spdx_repodir, self.base.conf.spdx_download)

    def Read_ConfigFile(self, display_pkgs, selected_pkgs):
        f = open(self.CONFIG_FILE, "r")
        get_text = f.read()
        config_list = get_text.split('\n')

        for pkg in display_pkgs:
            if pkg.name in config_list:
                selected_pkgs.append(pkg)
        selected_pkgs = list(set(selected_pkgs))
        f.close()
        return selected_pkgs

    def Save_ConfigFile(self, selected_pkgs, file_name, mode):
        save_list = []
        for pkg in selected_pkgs:
            save_list.append(pkg.name)

        f = open(file_name, mode)
        for line in save_list:
            f.write(line + '\n')
        f.close()

    def Read_Samples(self):
        sample_list = []
        if os.path.isdir(SAMPLE):
            for (root, dirs, filenames) in os.walk(SAMPLE):
                filenames.sort()
                for index in range(len(filenames)):
                    sample = ("Reference" + str(index+1) + "(" + filenames[index] + " based root file system)", filenames[index] + " based root file system", filenames[index])
                    sample_list.append(sample)
            return (True, sample_list)
        else:
            return (False, "There is no sample files")

    def PKGINSTDispMain(self):
        STAGE_INSTALL_TYPE = 1
        STAGE_CUSTOM_TYPE = 2
        STAGE_RECORD_INSTALL = 3
        STAGE_SAMPLE_INSTALL = 4
        STAGE_PKG_TYPE = 5
        STAGE_CUST_LIC = 6
        STAGE_PACKAGE = 7
        STAGE_PACKAGE_SPEC = 8
        STAGE_PROCESS = 9
        STAGE_GROUP = 10

        custom_type = NEW_INSTALL
        #----dnf part-------
        try:
            ypl = self.base.returnPkgLists(
                self.pkgnarrow, self.patterns, self.installed_available, self.reponame)
        except dnf.exceptions.Error as e:
            return 1, [str(e)]
        else:
            if len(ypl.available + ypl.installed) < 1:
                print ("Error! No packages!")
                sys.exit(0)
            self.screen = StartHotkeyScreen(_TXT_ROOT_TITLE)
            if self.screen == None:
                sys.exit(1)
            stage = STAGE_INSTALL_TYPE
 
            def __init_pkg_type():
                pkgTypeList = []
            
                pkgType_locale = pkgType("locale", False, "If select, you can see/select *-locale/*-localedata packages in the next step.")
                pkgTypeList.append(pkgType_locale)
                pkgType_dev = pkgType("dev", False, "If select, you can see/select *-dev packages in the next step.")
                pkgTypeList.append(pkgType_dev)
                pkgType_doc = pkgType("doc", False, "If select, you can see/select *-doc packages in the next step.")
                pkgTypeList.append(pkgType_doc)
                pkgType_dbg = pkgType("dbg", False, "If select, you can see/select *-dbg packages in the next step.")
                pkgTypeList.append(pkgType_dbg)
                pkgType_staticdev = pkgType("staticdev", False, "If select, you can see/select *-staticdev packages in the next step.")
                pkgTypeList.append(pkgType_staticdev)
                pkgType_ptest = pkgType("ptest", False, "If select, you can see/select *-ptest packages in the next step.")
                pkgTypeList.append(pkgType_ptest)

                return pkgTypeList

            pkgTypeList = __init_pkg_type()
            selected_pkgs = []
            selected_pkgs_spec = []
            pkgs_spec = []
            (Flag, sample_list) = self.Read_Samples()
            if Flag == True:
                for sample in sample_list:
                    Custom_actions.append(sample)

            while True:
                #==============================
                # select install type
                #==============================
                if stage == STAGE_INSTALL_TYPE:
                    self.install_type = PKGINSTActionWindowCtrl(self.screen, Install_actions, self.install_type)

                    if self.install_type == ACTION_INSTALL:
                        stage = STAGE_CUSTOM_TYPE
                        continue
                    else:
                        stage = STAGE_PACKAGE

                    selected_pkgs = []
                    selected_pkgs_spec = []
                    pkgs_spec = []
                    self.group_botton = False

                # ==============================
                # custom type
                # ==============================
                elif stage == STAGE_CUSTOM_TYPE:
                    (result, custom_type) = PKGCUSActionWindowCtrl(self.screen, Custom_actions, self.install_type)

                    # Read comps information
                    self.base.read_comps(arch_filter=True)
                    self.grps = self.base.comps.groups
                    if self.grps:
                        self.group_flag = True
                        self.group_botton = False

                    if result == "b":
                        # back
                        stage = STAGE_INSTALL_TYPE
                        continue

                    if custom_type == NEW_INSTALL:
                        stage = STAGE_PACKAGE
                        result = HotkeyExitWindow(self.screen, confirm_type=CONFIRM_LICENSE)
                        if result == "y":
                            self.no_gpl3 = False
                        else:
                            self.no_gpl3 = True
                    elif custom_type == RECORD_INSTALL:
                        stage = STAGE_RECORD_INSTALL
                        self.no_gpl3 = False
                    elif custom_type >= SAMPLE_INSTALL:
                        sample_type = custom_type-2
                        custom_type = SAMPLE_INSTALL
                        stage = STAGE_SAMPLE_INSTALL
                        self.no_gpl3 = False

                # ==============================
                # record install
                # ==============================
                elif stage == STAGE_RECORD_INSTALL:

                    (result, self.CONFIG_FILE) = PKGINSTPathInputWindow(self.screen, \
                                                      True, \
                                                      "  Config File  ", \
                                                      "Enter the name of configuration file you wish to load:", \
                                                      self.CONFIG_FILE )

                    if result == "cancel":
                        # back
                        stage = STAGE_CUSTOM_TYPE
                        continue

                    else:
                        # next
                        stage = STAGE_PACKAGE

                # ==============================
                # sample install
                # ==============================
                elif stage == STAGE_SAMPLE_INSTALL:
                    config_file = SAMPLE + '/' + sample_list[sample_type][2]
                    try:
                        f = open(config_file, "r")
                    except Exception as e:
                        logger.error(_("%s."), e)
                        StopHotkeyScreen(self.screen)
                        self.screen = None
                        sys.exit(0)
                    #get_text = f.read()
                    #config_list = get_text.split('\n')
                    #config_list.pop()
                    #stage = STAGE_PROCESS
                    self.CONFIG_FILE = config_file
                    stage = STAGE_PACKAGE

                #==============================
                # Grouplist 
                #==============================
                elif stage == STAGE_GROUP:
                    group_list = []
                    for grp in self.grps:
                        group = (grp.ui_name, grp.ui_description, grp.mandatory_packages)
                        group_list.append(group)
                    
                    (result, group_id) = PKGCUSActionWindowCtrl(self.screen, group_list, self.install_type, True)

                    if result == "b":
                        # back
                        stage = STAGE_CUSTOM_TYPE
                        continue

                    elif result == "g":
                        #group
                        self.group_botton = False
                        stage = STAGE_PACKAGE
                        continue

                    else:
                        pkg_group = group_list[group_id][2]
                        stage = STAGE_PACKAGE


                #==============================
                # select package
                #==============================
                elif stage == STAGE_PACKAGE:
                    if self.group_flag == True and self.install_type == ACTION_INSTALL:
                        if self.group_botton == False:
                            (result, selected_pkgs, pkgs_spec) = self.PKGINSTWindowCtrl(None, \
                                                                                None, selected_pkgs, custom_type, pkg_group=[], group_hotkey=True)

                        else:
                            (result, selected_pkgs, pkgs_spec) = self.PKGINSTWindowCtrl(None, \
                                                                                None, selected_pkgs, custom_type, pkg_group)
                    else:
                        (result, selected_pkgs, pkgs_spec) = self.PKGINSTWindowCtrl(None, \
                                                                                None, selected_pkgs, custom_type)

                    if result == "b":
                        # back
                        if self.install_type == ACTION_INSTALL:
                            stage = STAGE_CUSTOM_TYPE
                        else:
                            stage = STAGE_INSTALL_TYPE
                            self.no_gpl3 = False

                        if self.group_botton == True:
                            stage = STAGE_GROUP
                        continue

                    if result == "g":
                        if self.group_flag == True and self.install_type == ACTION_INSTALL:
                            #group
                            self.group_botton = True
                            stage = STAGE_GROUP
                            continue

                    elif result == "n":
                        if self.install_type == ACTION_INSTALL:
                            stage = STAGE_PKG_TYPE
                        else:
                            #confirm if or not continue process function
                            install_type_switch = {ACTION_REMOVE: CONFIRM_REMOVE, \
                                                   ACTION_UPGRADE: CONFIRM_UPGRADE, \
                                                   ACTION_GET_PKG: CONFIRM_GET_PKG, \
                                                   ACTION_GET_SOURCE: CONFIRM_GET_SOURCE, \
                                                   ACTION_GET_SPDX: CONFIRM_GET_SPDX, \
                                                   ACTION_GET_ALL: CONFIRM_GET_ALL}
                            confirm_type = install_type_switch.get(self.install_type)

                            hkey = HotkeyExitWindow(self.screen, confirm_type)
                            if hkey == "y":
                                stage = STAGE_PROCESS
                            elif hkey == "n":
                                stage = STAGE_PACKAGE

                #==============================
                # select package type
                #==============================
                elif stage == STAGE_PKG_TYPE:
                    (result, pkgTypeList) = PKGTypeSelectWindowCtrl(self.screen, pkgTypeList)
                    if result == "b":
                        # back
                        stage = STAGE_PACKAGE
                    elif result == "n":
                        stage = STAGE_PACKAGE_SPEC

                #==============================
                # select special packages(local, dev, dbg, doc) 
                #==============================
                elif stage == STAGE_PACKAGE_SPEC:
                    (result, selected_pkgs_spec, pkgs_temp) = self.PKGINSTWindowCtrl(pkgTypeList, \
                                                                                pkgs_spec, selected_pkgs_spec, custom_type)
                    if result == "b":
                        # back
                        stage = STAGE_PKG_TYPE
                    elif result == "k":
                        stage = STAGE_PKG_TYPE
                    elif result == "n":
                        stage = STAGE_PROCESS

                # ==============================
                # Process function
                # ==============================
                elif stage == STAGE_PROCESS:
                    if self.install_type == ACTION_INSTALL:
                        self.CONFIG_FILE = ".config"
                        (result, self.CONFIG_FILE) = PKGINSTPathInputWindow(self.screen, \
                                                      False, \
                                                      "  Config File  ", \
                                                      "Enter the name of configuration file you wish to save:", \
                                                      self.CONFIG_FILE )
                    if result == "cancel":
                        # save config file
                        self.SAVE = False

                    if self.install_type == ACTION_GET_SOURCE or self.install_type == ACTION_GET_SPDX:
                        self.GET_SOURCE_or_SPDX(selected_pkgs)
                        break
                    if self.install_type == ACTION_GET_PKG:
                        self.GET_RKG(selected_pkgs)
                        break
                    if self.install_type == ACTION_GET_ALL:
                        self.GET_ALL(selected_pkgs)
                        break
                    else:
                        for pkg in selected_pkgs:           #selected_pkgs
                            if self.install_type == ACTION_INSTALL:
                                s_line = ["install", pkg.name]
                            elif self.install_type == ACTION_REMOVE:
                                s_line = ["remove", pkg.name]
                            elif self.install_type == ACTION_UPGRADE:
                                s_line = ["upgrade", pkg.name]
                            self.run_dnf_command(s_line)

                        if self.install_type == ACTION_INSTALL:
                            if self.SAVE == True:
                                self.Save_ConfigFile(selected_pkgs, self.CONFIG_FILE, "w")
                                #selected_pkgs_spec
                                if selected_pkgs_spec:
                                    self.Save_ConfigFile(selected_pkgs_spec, self.CONFIG_FILE, "a")
 
                            for pkg in selected_pkgs_spec:
                                s_line = ["install", pkg.name]
                                self.run_dnf_command(s_line)

                        if self.no_gpl3:
                            #obtain the transaction
                            self.base.resolve(self.cli.demands.allow_erasing)
                            install_set = self.base.transaction.install_set

                            result = self.showChangeSet(install_set)
                            #continue to install
                            if result == "y":
                                if self.install_type == ACTION_INSTALL:
                                    confirm_type = CONFIRM_INSTALL

                                hkey = HotkeyExitWindow(self.screen, confirm_type)
 
                                if hkey == "y":
                                    if self.screen != None:
                                        StopHotkeyScreen(self.screen)
                                        self.screen = None
                                    if self.install_type != ACTION_REMOVE:
                                        self.base.conf.assumeyes = True
                                    break
                                elif hkey == "n":
                                    stage = STAGE_PKG_TYPE
                            #don't want to install GPLv3 that depended by others
                            elif result == "b":
                                stage = STAGE_PKG_TYPE
                            elif result == "n":
                                if self.install_type == ACTION_INSTALL:
                                    confirm_type = CONFIRM_INSTALL

                                hkey = HotkeyExitWindow(self.screen, confirm_type)
 
                                if hkey == "y":
                                    if self.screen != None:
                                        StopHotkeyScreen(self.screen)
                                        self.screen = None
                                    if self.install_type != ACTION_REMOVE:
                                        self.base.conf.assumeyes = True
                                    break

                        else:
                            if self.screen != None:
                                StopHotkeyScreen(self.screen)
                                self.screen = None
                                if self.install_type != ACTION_REMOVE:
                                    self.base.conf.assumeyes = True
                            break

            if self.screen != None:
                StopHotkeyScreen(self.screen)
                self.screen = None

    def _DeleteUpgrade(self,packages=None,display_pkgs=[]):
        haveUpgrade=False
        for i, pkg in enumerate(display_pkgs[:-1]):
            for pkg_oth in display_pkgs[i+1:]:
                if pkg.name==pkg_oth.name:
                    haveUpgrade=True
                    break
            if haveUpgrade :
                break
        ctn=0
        if(haveUpgrade):
            for pkg in packages:
                if  (not pkg.installed) and (pkg in display_pkgs):
                    ctn+=1
                    display_pkgs.remove(pkg)
        return haveUpgrade

    def PkgType_filter(self, display_pkgs, packages, pkgTypeList):
        pkgType_dic= dict()  
        Type_status = False
        for pkgType in pkgTypeList:
            pkgType_dic[pkgType.name] = pkgType.status
            if pkgType.status == True:
                Type_status = True

        if Type_status:
            #Don't show doc and dbg packages
            strings_pattern_end = ('-dev', '-doc', '-dbg', '-staticdev', '-ptest')
            for pkg in packages:
                if "-locale-" in pkg.name and not pkgType_dic["locale"]:
                    display_pkgs.remove(pkg)
                elif "-localedata-" in pkg.name and not pkgType_dic["locale"]:
                    display_pkgs.remove(pkg)
                elif pkg.name.endswith(strings_pattern_end):
                    index = pkg.name.rindex('-')
                    string_pattern = pkg.name[index+1:]
                    if not pkgType_dic[string_pattern]:
                        display_pkgs.remove(pkg)

        else:
            display_pkgs = []

        return display_pkgs

    def PKGINSTWindowCtrl(self, pkgTypeList, packages=None, selected_pkgs=[], custom_type=0, pkg_group=[], group_hotkey=False):
        STAGE_SELECT = 1
        STAGE_PKG_TYPE = 2
        STAGE_BACK   = 3
        STAGE_INFO   = 4
        STAGE_EXIT   = 5
        STAGE_SEARCH = 6
        STAGE_NEXT = 7
        STAGE_GROUP = 8

        iTargetSize = 0
        iHostSize = 0

        searched_ret = [] 
        pkgs_spec = []
        position = 0
        search_position = 0
        check = 0
        stage = STAGE_SELECT
        search = None

        hotkey_switch = {"n": STAGE_NEXT, \
                     "b": STAGE_BACK, \
                     "i": STAGE_INFO, \
                     "x": STAGE_EXIT, \
                     "g": STAGE_GROUP, \
                     "r": STAGE_SEARCH}
 
        try:
            ypl = self.base.returnPkgLists(
                self.pkgnarrow, self.patterns, self.installed_available, self.reponame)
        except dnf.exceptions.Error as e:
            return 1, [str(e)]
 
        if pkgTypeList == None:
            pkg_available = copy.copy(ypl.available)
            pkg_installed = copy.copy(ypl.installed)
            packages = ypl.installed + ypl.available
            display_pkgs = pkg_installed + pkg_available
            sorted(packages)
            sorted(display_pkgs)
        else:
            display_pkgs = copy.copy(packages)

        if self.no_gpl3:
            for pkg in packages:
                license = pkg.license
                if license:
                    if "GPLv3" in license:
                        display_pkgs.remove(pkg)
            packages = copy.copy(display_pkgs) #backup all pkgs

        if pkgTypeList != None:
            display_pkgs = self.PkgType_filter(display_pkgs, packages, pkgTypeList)

            actions = (ACTION_REMOVE, ACTION_UPGRADE, ACTION_GET_PKG, ACTION_GET_SOURCE, ACTION_GET_SPDX, ACTION_GET_ALL)
            if self.install_type in actions:
                for pkg in packages:
                    if pkg not in ypl.installed:
                        if pkg in display_pkgs:
                            display_pkgs.remove(pkg)

            elif self.install_type == ACTION_INSTALL:
                if(self._DeleteUpgrade(packages,display_pkgs)):
                    hkey = HotkeyAttentionWindow(self.screen, ATTENTON_HAVE_UPGRADE)

            if len(display_pkgs) == 0:
                if not self.no_gpl3:
                    if self.install_type == ACTION_INSTALL     :
                        confirm_type = CONFIRM_INSTALL
                        hkey = HotkeyExitWindow(self.screen, confirm_type)
                        if custom_type >= RECORD_INSTALL:
                            selected_pkgs = []
                            selected_pkgs = self.Read_ConfigFile(packages, selected_pkgs)
                        if hkey == "y":
                            return ("n", selected_pkgs, packages)
                        elif hkey == "n":
                            return ("k", selected_pkgs, packages)
                    else:
                        hkey=HotkeyAttentionWindow(self.screen,ATTENTON_NONE)
                        return ("b", selected_pkgs, packages)
                else:
                    return ("n", selected_pkgs, packages)
        else:
            #filter the type pkg such as -dev (Round1)
            if self.install_type == ACTION_INSTALL:
                strings_pattern_end = ('-dev', '-doc', '-dbg', '-staticdev', '-ptest')
                for pkg in packages:
                    if "-locale-" in pkg.name:
                        display_pkgs.remove(pkg)
                        pkgs_spec.append(pkg)
                    elif "-localedata-" in pkg.name:
                        display_pkgs.remove(pkg)
                        pkgs_spec.append(pkg)
                    elif pkg.name.endswith(strings_pattern_end):
                        display_pkgs.remove(pkg)
                        pkgs_spec.append(pkg)

                if(self._DeleteUpgrade(packages,display_pkgs)):
                    hkey = HotkeyAttentionWindow(self.screen, ATTENTON_HAVE_UPGRADE)

                if self.group_flag == True and self.group_botton == True:
                    groupinfo = []
                    for pkg in pkg_group:
                       groupinfo.append(pkg.name)
                    display_pkgs = []
                    for pkg in packages:
                       if pkg.name in groupinfo:
                           display_pkgs.append(pkg)

            #Except install
            else:
                for pkg in packages:
                    if pkg not in ypl.installed:
                        if pkg in display_pkgs:
                            display_pkgs.remove(pkg)
                display_pkgs = sorted(display_pkgs)

            if self.install_type == ACTION_UPGRADE:
                self.base.upgrade_all()
                self.base.resolve(self.cli.demands.allow_erasing)
                install_set = self.base.transaction.install_set
              
                display_pkgs = []
                for pkg in install_set:
                    display_pkgs.append(pkg)
                display_pkgs = sorted(display_pkgs)

                # clean the _transaction
                #self.base.close()
                self.base._transaction = None

        if len(display_pkgs)==0:
            if self.install_type==ACTION_INSTALL:
                stage = STAGE_NEXT
            elif self.install_type==ACTION_UPGRADE:
                hkey = HotkeyAttentionWindow(self.screen, ATTENTON_NONE_UPGRADE)
                return ("b", selected_pkgs, packages)
            else:
                hkey = HotkeyAttentionWindow(self.screen, ATTENTON_NONE)
                return ("b", selected_pkgs, packages)

        if custom_type >= RECORD_INSTALL:
            selected_pkgs = []
            selected_pkgs = self.Read_ConfigFile(display_pkgs, selected_pkgs)

        while True:
            if stage == STAGE_SELECT:
                if search == None:
                    (hkey, position, pkglist) = PKGINSTPackageWindow(self.screen, \
                                                            display_pkgs, \
                                                            selected_pkgs, \
                                                            position, \
                                                            iTargetSize, \
                                                            iHostSize, \
                                                            search, \
                                                            self.install_type, group_hotkey)
                else:
                    (hkey, search_position, pkglist) = PKGINSTPackageWindow(self.screen, \
                                                             searched_ret, \
                                                             selected_pkgs, \
                                                             search_position, \
                                                             iTargetSize, \
                                                             iHostSize, \
                                                             search, \
                                                             self.install_type, group_hotkey)

                stage = hotkey_switch.get(hkey, None)

            elif stage == STAGE_NEXT:
                search = None
                #if in packages select Interface:
                if pkgTypeList == None:
                    return ("n", selected_pkgs, pkgs_spec)
                #if in special type packages(dev,doc,locale) select Interface:
                else:
                    if not self.no_gpl3:
                        if self.install_type == ACTION_INSTALL : confirm_type = CONFIRM_INSTALL

                        hkey = HotkeyExitWindow(self.screen, confirm_type)
                        if hkey == "y":
                            return ("n", selected_pkgs, packages)
                        elif hkey == "n":
                            stage = STAGE_SELECT
                    else:
                        return ("n", selected_pkgs, packages)
            elif stage == STAGE_BACK:
                if not search == None:
                    stage = STAGE_SELECT
                    search = None
                else:
                    return ("b", selected_pkgs, pkgs_spec)
            elif stage == STAGE_GROUP:
                if not search == None:
                    stage = STAGE_SELECT
                    search = None
                else:
                    return ("g", selected_pkgs, pkgs_spec)
            elif stage == STAGE_INFO:
                if not search == None:
                    PKGINSTPackageInfoWindow(self.screen, searched_ret[search_position])
                else:
                    PKGINSTPackageInfoWindow(self.screen, display_pkgs[position])
                stage = STAGE_SELECT
            elif stage == STAGE_EXIT:
                hkey = HotkeyExitWindow(self.screen)
                if hkey == "y":
                    if self.screen != None:
                        StopHotkeyScreen(self.screen)
                        self.screen = None
                    sys.exit(0)
                elif hkey == "n":
                    stage = STAGE_SELECT
            elif stage == STAGE_SEARCH:
                search_position = 0
                search = PKGINSTPackageSearchWindow(self.screen)
                if not search == None:
                    def __search_pkgs(keyword, pkgs):
                        searched_pgks = []
                        keyword = re.escape(keyword)
                        for pkg in pkgs:
                            if re.compile(keyword, re.IGNORECASE).search(pkg.name):
                                searched_pgks.append(pkg)
                        return searched_pgks
                    searched_ret = __search_pkgs(search, display_pkgs)
                    if len(searched_ret) == 0:
                        buttons = ['OK']
                        (w, h) = GetButtonMainSize(self.screen)
                        rr = ButtonInfoWindow(self.screen, "Message", "%s - not found." % search, w, h, buttons)
                        search = None
                stage = STAGE_SELECT

    def showChangeSet(self, pkgs_set):
        gplv3_pkgs = []
        #pkgs = self.opts.pkg_specs
        for pkg in pkgs_set:
            license = pkg.license
            if license:
                if "GPLv3" in license:
                    gplv3_pkgs.append(pkg)
        if len(gplv3_pkgs) > 0:
            hkey = ConfirmGplv3Window(self.screen, gplv3_pkgs)
            if hkey == "b":
                return "b"
            elif hkey == "n":
                return "n"
        else:
            return "y"
