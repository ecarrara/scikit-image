from util import prepare_for_display, window_manager, GuiLockError
import numpy as np
import sys

# We try to aquire the gui lock first or else the gui import might
# trample another GUI's PyOS_InputHook.
window_manager.acquire('qt')

try:
    from PyQt4.QtGui import (QApplication, QMainWindow, QImage, QPixmap,
                             QLabel, QWidget)
    from PyQt4 import QtCore, QtGui

except ImportError:
    window_manager._release('qt')

    raise ImportError("""\
    PyQt4 libraries not installed. Please refer to

    http://www.riverbankcomputing.co.uk/software/pyqt/intro

    for more information.  PyQt4 is GPL licensed.  For an
    LGPL equivalent, see

    http://www.pyside.org
    """)

app = None

class ImageLabel(QLabel):
    def __init__(self, parent, arr):
        QLabel.__init__(self)

        # we need to hold a reference to
        # arr because QImage doesn't copy the data
        # and the buffer must be alive as long
        # as the image is alive.
        self.arr = arr

        # we also need to pass in the row-stride to
        # the constructor, because we can't guarantee
        # that every row of the numpy data is
        # 4-byte aligned. Which Qt would require
        # if we didnt pass the stride.
        self.img = QImage(arr.data, arr.shape[1], arr.shape[0],
                          arr.strides[0], QImage.Format_RGB888)
        self.pm = QPixmap.fromImage(self.img)
        self.setPixmap(self.pm)
        self.setAlignment(QtCore.Qt.AlignTop)
        self.setMinimumSize(100, 100)

    def resizeEvent(self, evt):
        width = self.width()
        pm = QPixmap.fromImage(self.img)
        self.pm = pm.scaledToWidth(width)
        self.setPixmap(self.pm)


class ImageWindow(QMainWindow):
    def __init__(self, arr, mgr):
        QMainWindow.__init__(self)
        self.setWindowTitle('scikits.image')
        self.mgr = mgr
        self.main_widget = QWidget()
        self.layout = QtGui.QGridLayout(self.main_widget)
        self.setCentralWidget(self.main_widget)

        self.label = ImageLabel(self, arr)
        self.layout.addWidget(self.label, 0, 0)
        self.layout.addLayout
        self.mgr.add_window(self)
        self.main_widget.show()

    def closeEvent(self, event):
        # Allow window to be destroyed by removing any
        # references to it
        self.mgr.remove_window(self)


def imread(filename, as_grey=False):
    """
    Read an image using QT's QImage.load
    """
    qtimg = QImage()
    if not qtimg.load(filename):
        # QImage.load() returns false on failure, so raise an exception
        raise IOError('Unable to load file %s' % filename)
    if qtimg.depth() == 1:
        raise IOError('1-bit images currently not supported')
    # TODO: Warn about other odd formats we don't currently handle properly,
    # such as the odd 16-bit packed formats QT supports
    arrayptr = qtimg.bits()
    # QT may pad the image, so we need to use bytesPerLine, not width for
    # the conversion to a numpy array
    bytesPerPixel = qtimg.depth() // 8
    pixelsPerLine = qtimg.bytesPerLine() // bytesPerPixel
    img_size = pixelsPerLine * qtimg.height() * bytesPerPixel
    arrayptr.setsize(img_size)
    img = np.array(arrayptr)
    # Reshape and trim down to correct dimensions
    if bytesPerPixel > 1:
        img = img.reshape((qtimg.height(), pixelsPerLine, bytesPerPixel))
        img = img[:, :qtimg.width(), :]
    else:
        img = img.reshape((qtimg.height(), pixelsPerLine))
        img = img[:, :qtimg.width()]
    if as_grey and bytesPerPixel > 1:
        # Stolen from fits_plugin
        # these are the values that wikipedia says are typical
        transform = numpy.array([ 0.30,  0.59,  0.11])
        return numpy.dot(img, transform)
    return img


def imshow(arr, fancy=False):
    global app
    if not app:
        app = QApplication([])

    arr = prepare_for_display(arr)

    if not fancy:
        iw = ImageWindow(arr, window_manager)
    else:
        from scivi import SciviImageWindow
        iw = SciviImageWindow(arr, window_manager)

    iw.show()


def _app_show():
    global app
    if app and window_manager.has_windows():
        app.exec_()
    else:
        print 'No images to show.  See `imshow`.'


def imsave(filename, img):
    # we can add support for other than 3D uint8 here...
    img = prepare_for_display(img)
    qimg = QImage(img.data, img.shape[1], img.shape[0],
                          img.strides[0], QImage.Format_RGB888)
    saved = qimg.save(filename)
    if not saved:
        from textwrap import dedent
        msg = dedent(
            '''The image was not saved. Allowable file formats
            for the QT imsave plugin are:
            BMP, JPG, JPEG, PNG, PPM, TIFF, XBM, XPM''')
        raise RuntimeError(msg)
