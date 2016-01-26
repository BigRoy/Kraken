import logging

class WidgetHandler(logging.StreamHandler):
    """
    This creates a custom logging handler object that allows for re-directing
    output to various locations.
    """

    def __init__(self,
                 widget=None):

        super(WidgetHandler, self).__init__()

        self.widget = widget

        # Set logging message output format
        # formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s\n\n')
        # self.setFormatter(formatter)


    def flush(self):
        super(WidgetHandler, self).flush()


    def emit(self, record):

        try:
            msg = self.format(record)

            if hasattr(self.widget, 'insertPlainText') and \
                    hasattr(self.widget, 'moveCursor'):
                self.widget.moveCursor(QTextCursor.End)
                self.widget.insertPlainText(msg)

            self.stream.write(msg)
            self.stream.write('\n')
            self.stream.flush()
            return msg

        except KeyboardInterrupt:
            raise KeyboardInterrupt

        except SystemExit:
            raise KeyboardInterrupt

        except Exception:
            self.handleError(record)