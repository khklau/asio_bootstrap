import hashlib
import os
import shutil
import subprocess
import tarfile
import urllib
import zipfile
from waflib import Logs
from waflib.extras.preparation import PreparationContext
from waflib.extras.build_status import BuildStatus
from waflib.extras.filesystem_utils import removeSubdir
from waflib.extras.mirror import MirroredTarFile, MirroredZipFile
from waflib.Build import InstallContext

__asioVersion = '1.10.6'
__downloadUrl = 'http://sourceforge.net/projects/asio/files/asio/%s (Stable)/%s/download'
__posixFile = 'asio-%s.tar.bz2' % __asioVersion
__posixSha256Checksum = '\xe0\xd7\x1c\x40\xa7\xb1\xf6\xc1\x33\x40\x08\xfb\x27\x9e\x73\x61\xb3\x2a\x06\x3e\x02\x0e\xfd\x21\xe4\x0d\x9d\x8f\xf0\x37\x19\x5e'
__ntFile = 'asio-%s.zip' % __asioVersion
__ntSha256Checksum = '\xef\x45\x7d\x6b\xc1\xd5\xbe\x27\xa8\x50\x23\x3d\x6e\xe5\x12\xb5\x6d\xa9\xd3\x02\x70\x10\x79\x60\xbd\x6f\xf5\x21\x9e\xbf\xbe\x66'
__srcDir = 'src'

def options(optCtx):
    optCtx.recurse('env')
    optCtx.load('cxx_env dep_resolver')

def prepare(prepCtx):
    prepCtx.options.dep_base_dir = prepCtx.srcnode.find_dir('..').abspath()
    prepCtx.recurse('env')
    prepCtx.load('cxx_env dep_resolver')
    status = BuildStatus.init(prepCtx.path.abspath())
    if status.isSuccess():
	prepCtx.msg('Preparation already complete', 'skipping')
	return
    if os.name == 'posix':
	file = MirroredTarFile(
		__posixSha256Checksum,
		__downloadUrl % (__asioVersion, __posixFile),
		os.path.join(prepCtx.path.abspath(), __posixFile))
    elif os.name == 'nt':
	file = MirroredZipFile(
		__ntSha256Checksum,
		__downloadUrl % (__asioVersion, __ntFile),
		os.path.join(prepCtx.path.abspath(), __ntFile))
    else:
	prepCtx.fatal('Unsupported OS %s' % os.name)
    prepCtx.msg('Synchronising', file.getSrcUrl())
    if file.sync(10):
	prepCtx.msg('Saved to', file.getTgtPath())
    else:
	prepCtx.fatal('Synchronisation failed')
    extractDir = 'asio-%s' % __asioVersion
    removeSubdir(prepCtx.path.abspath(), __srcDir, extractDir, 'include')
    prepCtx.start_msg('Extracting files to')
    file.extract(prepCtx.path.abspath())
    os.rename(extractDir, __srcDir)
    prepCtx.end_msg(os.path.join(prepCtx.path.abspath(), __srcDir))

def configure(confCtx):
    confCtx.options.env_conf_dir = confCtx.srcnode.find_dir('env').abspath()
    confCtx.recurse('env')
    confCtx.load('cxx_env dep_resolver')
    status = BuildStatus.init(confCtx.path.abspath())
    if status.isSuccess():
	confCtx.msg('Configuration already complete', 'skipping')
	return
    srcPath = os.path.join(confCtx.path.abspath(), __srcDir)
    os.chdir(srcPath)
    if os.name == 'posix':
	returnCode = subprocess.call([
		'sh',
		os.path.join(srcPath, 'configure'),
		'--prefix=%s' % confCtx.srcnode.abspath(),
		'--without-boost'])
	if returnCode != 0:
	    confCtx.fatal('Asio configure failed: %d' % returnCode)
    elif os.name == 'nt':
	# Nothing to do, just use the provided Nmake file
	return
    else:
	confCtx.fatal('Unsupported OS %s' % os.name)

def build(buildCtx):
    status = BuildStatus.load(buildCtx.path.abspath())
    if status.isSuccess() and not(isinstance(buildCtx, InstallContext)):
	Logs.pprint('NORMAL', 'Build already complete                   :', sep='')
	Logs.pprint('GREEN', 'skipping')
	return
    srcPath = os.path.join(buildCtx.path.abspath(), __srcDir)
    os.chdir(srcPath)
    returnCode = 0
    if os.name == 'posix' and not(isinstance(buildCtx, InstallContext)):
	returnCode = subprocess.call([
		'make',
		'install'])
    elif os.name == 'nt' and not(isinstance(buildCtx, InstallContext)):
	returnCode = subprocess.call([
		'nmake',
		'-f',
		os.path.join(srcPath, 'src', 'Makefile.msc')])
    elif not(isinstance(buildCtx, InstallContext)):
	confCtx.fatal('Unsupported OS %s' % os.name)
    if returnCode != 0:
	buildCtx.fatal('Asio build failed: %d' % returnCode)
    buildCtx.shlib(
	    name='shlib_asio',
	    source=[buildCtx.path.find_node('src.cxx')],
	    target='asio',
	    includes=[os.path.join(buildCtx.path.abspath(), 'include')],
	    defines=['ASIO_STANDALONE', 'ASIO_SEPARATE_COMPILATION', 'ASIO_DYN_LINK'],
	    cxxflags=buildCtx.env.CXXFLAGS,
	    linkflags=buildCtx.env.LDFLAGS,
	    install_path=os.path.join(buildCtx.path.abspath(), 'lib'))
    buildCtx.stlib(
	    name='stlib_asio',
	    source=[buildCtx.path.find_node('src.cxx')],
	    target='asio',
	    includes=[os.path.join(buildCtx.path.abspath(), 'include')],
	    defines=['ASIO_STANDALONE', 'ASIO_SEPARATE_COMPILATION'],
	    cxxflags=buildCtx.env.CXXFLAGS,
	    linkflags=buildCtx.env.LDFLAGS,
	    install_path=os.path.join(buildCtx.path.abspath(), 'lib'))
    status.setSuccess()
