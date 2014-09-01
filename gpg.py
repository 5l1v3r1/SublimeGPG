# -*- coding: utf-8 -*-

"""GPG plugin for Sublime Text 3.

This GPG plugin for Sublime Text 3 adds commands to decrypt, encrypt, sign, and
authenticate documents.
"""

__author__ = 'crowsonkb@gmail.com (Katherine Crowson)'

import sublime, sublime_plugin

import binascii
import platform
import shutil
import subprocess

PIPE = subprocess.PIPE


def gpg(view, data, opts_in):
    """gpg calls the gpg binary to process the data and returns the result."""

    window = view.window()
    s = sublime.load_settings('gpg.sublime-settings')
    gpg_command = s.get('gpg_command')
    opts = [gpg_command,
            '--armor',
            '--batch',
            '--trust-model', 'always',
            '--yes']
    homedir = s.get('homedir')
    if homedir:
        opts += ['--homedir', homedir]
    for _ in range(0, s.get('verbosity')):
        opts.append('--verbose')
    opts += opts_in
    try:
        gpg_process = subprocess.Popen(opts, universal_newlines=False,
                                       stdin=PIPE, stdout=PIPE, stderr=PIPE)
        if view.encoding() != 'Hexadecimal':
            result, error = gpg_process.communicate(input=data.encode())
        else:
            binary_data = binascii.unhexlify(
                data.translate(str.maketrans('', '', ' \r\n')).encode())
            result, error = gpg_process.communicate(input=binary_data)
        if error:
            panel(window, error.decode())
        if gpg_process.returncode:
            return None
        return result.decode()
    except IOError as e:
        panel(window, 'Error: %s' % e)
        return None
    except OSError as e:
        panel(window, 'Error: %s' % e)
        return None
    except binascii.Error as e:
        panel(window, 'Error: %s' % e)
        return None


def panel(window, message):
    """panel displays gpg's stderr at the bottom of the window."""

    p = window.create_output_panel('gpg_message')
    p.run_command('gpg_message', {'message': message})
    p.show(p.size())
    window.run_command('show_panel', {'panel': 'output.gpg_message'})


class GpgMessageCommand(sublime_plugin.TextCommand):
    """A helper command for panel."""

    def run(self, edit, message):
        self.view.insert(edit, self.view.size(), message)


class GpgCommand(sublime_plugin.TextCommand):
    """A helper command to replace the document content with new content."""

    def run(self, edit, opts):
        doc = sublime.Region(0, self.view.size())
        data = gpg(self.view, self.view.substr(doc), opts)
        if data:
            self.view.replace(edit, doc, data)

def get_recipients_from_text(window):
    view = window.active_view()
    #doc = sublime.Region(0, view.size())
    first_lines = sublime.Region(0, view.text_point(4, 0))
    print(repr(first_lines))
    text = view.substr(first_lines)
    print(repr(text))
    print(repr("recipients:" in text))

    key = "recipients:"
    if key in text:
        index = text.index(key)
        text = text[index+len(key):]
        if "\n" in text:
            index = text.index("\n")
            text = text[0:index]
        recipients = [recipient.strip() for recipient in text.split(",")]
        return recipients
    else:
        return None

def get_recipients(window, on_done):
    recipients = get_recipients_from_text(window)
    if recipients is not None:
        on_done(recipients)
    else:
        window.show_input_panel('Recipient:', '', lambda recipient: on_done(recipient), None, None)

def format_recipients(recipients):
    opts = []
    for recipient in recipients:
        opts.append("--recipient")
        opts.append(recipient)
    return opts

class GpgDecryptCommand(sublime_plugin.WindowCommand):
    """Decrypts an OpenPGP format message."""

    def run(self):
        opts = []
        self.window.active_view().run_command('gpg', {'opts': opts})


class GpgEncryptCommand(sublime_plugin.WindowCommand):
    """Encrypts plaintext to an OpenPGP format message."""

    def run(self):
        get_recipients(self.window, self.on_done)

    def on_done(self, recipients):
        opts = ['--encrypt'] + format_recipients(recipients)
        self.window.active_view().run_command('gpg', {'opts': opts})


class GpgSignCommand(sublime_plugin.WindowCommand):
    """Signs the document using a clear text signature."""

    def run(self):
        opts = ['--clearsign']
        self.window.active_view().run_command('gpg', {'opts': opts})


class GpgSignAndEncryptCommand(sublime_plugin.WindowCommand):
    """Encrypts plaintext to a signed OpenPGP format message."""

    def run(self):
        get_recipients(self.window, self.on_done)

    def on_done(self, recipients):
        opts = ['--sign',
                '--encrypt'
                ] + format_recipients(recipients)
        self.window.active_view().run_command('gpg', {'opts': opts})


class GpgVerifyCommand(sublime_plugin.WindowCommand):
    """Verifies the document's signature without altering the document."""

    def run(self):
        opts = ['--verify']
        self.window.active_view().run_command('gpg', {'opts': opts})
