"""
Email UI components for the Knowledge Mesh Desktop application.

This module provides UI components for displaying and interacting with emails.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set, Callable, Union
import json

from PyQt5.QtCore import Qt, QSize, QPoint, QRect, QTimer, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen, QBrush, QPainterPath, QLinearGradient
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit,
                           QScrollArea, QFrame, QSplitter, QTabWidget, QComboBox, QCheckBox, QDateEdit,
                           QListWidget, QListWidgetItem, QMenu, QAction, QToolBar, QToolButton, QSizePolicy)

from src.core.config import Config
from src.core.events import EventType, publish_event, subscribe_event
from src.models.email import Email, EmailAddress, EmailFolder, EmailSearchQuery, EmailSearchResult
from src.services.email_connector import EmailConnectorService
from src.services.email_processor import EmailProcessorService
from src.services.email_search import EmailSearchService
from src.ui.theme_selector import ThemeSelectorWidget


logger = logging.getLogger(__name__)


class EmailListItem(QWidget):
    """Widget for displaying an email in a list."""
    
    clicked = pyqtSignal(Email)
    
    def __init__(self, email: Email, parent=None):
        """Initialize the email list item widget."""
        super().__init__(parent)
        self.email = email
        self.hovered = False
        self.selected = False
        
        self.setMinimumHeight(80)
        self.setMaximumHeight(100)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        self.from_label = QLabel(self.email.from_address.name if self.email.from_address and self.email.from_address.name else 
                                self.email.from_address.address if self.email.from_address else "Unknown")
        self.from_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.from_label)
        
        self.date_label = QLabel(self.format_date(self.email.date))
        self.date_label.setAlignment(Qt.AlignRight)
        header_layout.addWidget(self.date_label)
        
        layout.addLayout(header_layout)
        
        self.subject_label = QLabel(self.email.subject)
        self.subject_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.subject_label)
        
        preview_text = self.email.body_text[:100] + "..." if len(self.email.body_text) > 100 else self.email.body_text
        self.preview_label = QLabel(preview_text)
        self.preview_label.setStyleSheet("color: #666;")
        layout.addWidget(self.preview_label)
        
        self.update_read_status()
    
    def format_date(self, date: datetime) -> str:
        """Format date for display."""
        now = datetime.now()
        
        if date.date() == now.date():
            return date.strftime("%H:%M")
        elif date.date() == (now - timedelta(days=1)).date():
            return "Yesterday"
        elif date.date() > (now - timedelta(days=7)).date():
            return date.strftime("%A")
        else:
            return date.strftime("%Y-%m-%d")
    
    def update_read_status(self):
        """Update the style based on read status."""
        if not self.email.is_read:
            self.setStyleSheet("background-color: rgba(0, 120, 215, 0.1);")
            self.from_label.setStyleSheet("font-weight: bold;")
            self.subject_label.setStyleSheet("font-weight: bold;")
        else:
            self.setStyleSheet("")
            self.from_label.setStyleSheet("")
            self.subject_label.setStyleSheet("")
    
    def enterEvent(self, event):
        """Handle mouse enter event."""
        self.hovered = True
        self.update()
    
    def leaveEvent(self, event):
        """Handle mouse leave event."""
        self.hovered = False
        self.update()
    
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.email)
    
    def paintEvent(self, event):
        """Paint the widget."""
        super().paintEvent(event)
        
        if self.hovered or self.selected:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            if self.selected:
                color = QColor(0, 120, 215, 50)
            else:
                color = QColor(0, 0, 0, 20)
                
            painter.fillRect(self.rect(), color)
            
            painter.end()
    
    def set_selected(self, selected: bool):
        """Set the selected state."""
        self.selected = selected
        self.update()


class EmailListWidget(QScrollArea):
    """Widget for displaying a list of emails."""
    
    email_selected = pyqtSignal(Email)
    
    def __init__(self, parent=None):
        """Initialize the email list widget."""
        super().__init__(parent)
        self.emails = []
        self.email_items = []
        self.selected_email = None
        
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(1)
        self.layout.addStretch()
        
        self.setWidget(self.container)
    
    def set_emails(self, emails: List[Email]):
        """Set the emails to display."""
        self.emails = emails
        self.selected_email = None
        self.update_list()
    
    def update_list(self):
        """Update the email list."""
        for item in self.email_items:
            self.layout.removeWidget(item)
            item.deleteLater()
        
        self.email_items = []
        
        for email in self.emails:
            item = EmailListItem(email)
            item.clicked.connect(self.on_email_clicked)
            self.layout.insertWidget(self.layout.count() - 1, item)
            self.email_items.append(item)
    
    def on_email_clicked(self, email: Email):
        """Handle email click event."""
        for item in self.email_items:
            item.set_selected(item.email.id == email.id)
        
        self.selected_email = email
        self.email_selected.emit(email)


class EmailViewWidget(QWidget):
    """Widget for displaying an email."""
    
    reply_clicked = pyqtSignal(Email)
    forward_clicked = pyqtSignal(Email)
    delete_clicked = pyqtSignal(Email)
    
    def __init__(self, parent=None):
        """Initialize the email view widget."""
        super().__init__(parent)
        self.email = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        self.subject_label = QLabel()
        self.subject_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.subject_label)
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(5)
        
        self.reply_button = QPushButton("Reply")
        self.reply_button.clicked.connect(self.on_reply_clicked)
        actions_layout.addWidget(self.reply_button)
        
        self.forward_button = QPushButton("Forward")
        self.forward_button.clicked.connect(self.on_forward_clicked)
        actions_layout.addWidget(self.forward_button)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        actions_layout.addWidget(self.delete_button)
        
        header_layout.addLayout(actions_layout)
        
        layout.addLayout(header_layout)
        
        metadata_layout = QVBoxLayout()
        metadata_layout.setSpacing(5)
        
        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("From:"))
        self.from_label = QLabel()
        from_layout.addWidget(self.from_label)
        from_layout.addStretch()
        metadata_layout.addLayout(from_layout)
        
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("To:"))
        self.to_label = QLabel()
        to_layout.addWidget(self.to_label)
        to_layout.addStretch()
        metadata_layout.addLayout(to_layout)
        
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date:"))
        self.date_label = QLabel()
        date_layout.addWidget(self.date_label)
        date_layout.addStretch()
        metadata_layout.addLayout(date_layout)
        
        layout.addLayout(metadata_layout)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        self.body_text = QTextEdit()
        self.body_text.setReadOnly(True)
        layout.addWidget(self.body_text)
        
        self.attachments_layout = QVBoxLayout()
        self.attachments_layout.setContentsMargins(0, 0, 0, 0)
        self.attachments_layout.setSpacing(5)
        
        self.attachments_label = QLabel("Attachments:")
        self.attachments_label.setVisible(False)
        self.attachments_layout.addWidget(self.attachments_label)
        
        self.attachments_container = QWidget()
        self.attachments_container.setLayout(QVBoxLayout())
        self.attachments_container.layout().setContentsMargins(0, 0, 0, 0)
        self.attachments_container.layout().setSpacing(5)
        self.attachments_layout.addWidget(self.attachments_container)
        
        layout.addLayout(self.attachments_layout)
        
        self.set_email(None)
    
    def set_email(self, email: Email):
        """Set the email to display."""
        self.email = email
        
        if not email:
            self.subject_label.setText("")
            self.from_label.setText("")
            self.to_label.setText("")
            self.date_label.setText("")
            self.body_text.setText("")
            self.attachments_label.setVisible(False)
            self.attachments_container.setVisible(False)
            return
        
        self.subject_label.setText(email.subject)
        
        if email.from_address:
            if email.from_address.name:
                self.from_label.setText(f"{email.from_address.name} <{email.from_address.address}>")
            else:
                self.from_label.setText(email.from_address.address)
        else:
            self.from_label.setText("Unknown")
        
        if email.to_addresses:
            to_text = ", ".join([f"{addr.name} <{addr.address}>" if addr.name else addr.address 
                               for addr in email.to_addresses])
            self.to_label.setText(to_text)
        else:
            self.to_label.setText("")
        
        self.date_label.setText(email.date.strftime("%Y-%m-%d %H:%M:%S"))
        
        if email.body_html:
            self.body_text.setHtml(email.body_html)
        else:
            self.body_text.setPlainText(email.body_text)
        
        self.update_attachments()
    
    def update_attachments(self):
        """Update the attachments display."""
        for i in reversed(range(self.attachments_container.layout().count())):
            widget = self.attachments_container.layout().itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        if not self.email or not self.email.attachments:
            self.attachments_label.setVisible(False)
            self.attachments_container.setVisible(False)
            return
        
        self.attachments_label.setVisible(True)
        self.attachments_container.setVisible(True)
        
        for attachment in self.email.attachments:
            attachment_widget = QWidget()
            attachment_layout = QHBoxLayout(attachment_widget)
            attachment_layout.setContentsMargins(0, 0, 0, 0)
            attachment_layout.setSpacing(5)
            
            icon_label = QLabel("📎")
            attachment_layout.addWidget(icon_label)
            
            filename_label = QLabel(attachment.filename)
            attachment_layout.addWidget(filename_label)
            
            size_label = QLabel(self.format_size(attachment.size))
            size_label.setStyleSheet("color: #666;")
            attachment_layout.addWidget(size_label)
            
            download_button = QPushButton("Download")
            download_button.clicked.connect(lambda _, a=attachment: self.on_download_attachment(a))
            attachment_layout.addWidget(download_button)
            
            attachment_layout.addStretch()
            
            self.attachments_container.layout().addWidget(attachment_widget)
    
    def format_size(self, size: int) -> str:
        """Format file size for display."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
    
    def on_reply_clicked(self):
        """Handle reply button click."""
        if self.email:
            self.reply_clicked.emit(self.email)
    
    def on_forward_clicked(self):
        """Handle forward button click."""
        if self.email:
            self.forward_clicked.emit(self.email)
    
    def on_delete_clicked(self):
        """Handle delete button click."""
        if self.email:
            self.delete_clicked.emit(self.email)
    
    def on_download_attachment(self, attachment):
        """Handle attachment download button click."""
        pass


class EmailSearchWidget(QWidget):
    """Widget for searching emails."""
    
    search_requested = pyqtSignal(EmailSearchQuery)
    
    def __init__(self, parent=None):
        """Initialize the email search widget."""
        super().__init__(parent)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search emails...")
        self.search_input.returnPressed.connect(self.on_search_clicked)
        search_layout.addWidget(self.search_input)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.on_search_clicked)
        search_layout.addWidget(self.search_button)
        
        self.advanced_button = QPushButton("Advanced")
        self.advanced_button.setCheckable(True)
        self.advanced_button.clicked.connect(self.on_advanced_toggled)
        search_layout.addWidget(self.advanced_button)
        
        layout.addLayout(search_layout)
        
        self.advanced_widget = QWidget()
        self.advanced_widget.setVisible(False)
        advanced_layout = QVBoxLayout(self.advanced_widget)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(10)
        
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Folder:"))
        
        self.folder_combo = QComboBox()
        for folder in EmailFolder:
            self.folder_combo.addItem(folder.name.capitalize(), folder)
        folder_layout.addWidget(self.folder_combo)
        
        advanced_layout.addLayout(folder_layout)
        
        address_layout = QHBoxLayout()
        
        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("From:"))
        self.from_input = QLineEdit()
        from_layout.addWidget(self.from_input)
        address_layout.addLayout(from_layout)
        
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("To:"))
        self.to_input = QLineEdit()
        to_layout.addWidget(self.to_input)
        address_layout.addLayout(to_layout)
        
        advanced_layout.addLayout(address_layout)
        
        date_layout = QHBoxLayout()
        
        date_from_layout = QHBoxLayout()
        date_from_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(datetime.now().date() - timedelta(days=30))
        date_from_layout.addWidget(self.date_from)
        date_layout.addLayout(date_from_layout)
        
        date_to_layout = QHBoxLayout()
        date_to_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(datetime.now().date())
        date_to_layout.addWidget(self.date_to)
        date_layout.addLayout(date_to_layout)
        
        advanced_layout.addLayout(date_layout)
        
        options_layout = QHBoxLayout()
        
        self.has_attachments_check = QCheckBox("Has attachments")
        options_layout.addWidget(self.has_attachments_check)
        
        self.unread_check = QCheckBox("Unread only")
        options_layout.addWidget(self.unread_check)
        
        advanced_layout.addLayout(options_layout)
        
        layout.addWidget(self.advanced_widget)
    
    def on_search_clicked(self):
        """Handle search button click."""
        query_text = self.search_input.text()
        
        if not query_text:
            return
        
        query = EmailSearchQuery.create(query_text=query_text)
        
        if self.advanced_widget.isVisible():
            folder_idx = self.folder_combo.currentIndex()
            if folder_idx >= 0:
                query.folder = self.folder_combo.itemData(folder_idx)
            
            if self.from_input.text():
                query.from_address = self.from_input.text()
            
            if self.to_input.text():
                query.to_address = self.to_input.text()
            
            query.date_from = datetime.combine(self.date_from.date().toPyDate(), datetime.min.time())
            query.date_to = datetime.combine(self.date_to.date().toPyDate(), datetime.max.time())
            
            if self.has_attachments_check.isChecked():
                query.has_attachments = True
            
            if self.unread_check.isChecked():
                query.is_read = False
        
        self.search_requested.emit(query)
    
    def on_advanced_toggled(self, checked):
        """Handle advanced button toggle."""
        self.advanced_widget.setVisible(checked)


class EmailComposeWidget(QWidget):
    """Widget for composing emails."""
    
    send_clicked = pyqtSignal(Email)
    cancel_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the email compose widget."""
        super().__init__(parent)
        self.reply_to = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        self.title_label = QLabel("New Email")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.title_label)
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(5)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.on_send_clicked)
        actions_layout.addWidget(self.send_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        actions_layout.addWidget(self.cancel_button)
        
        header_layout.addLayout(actions_layout)
        
        layout.addLayout(header_layout)
        
        recipients_layout = QVBoxLayout()
        recipients_layout.setSpacing(5)
        
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("To:"))
        self.to_input = QLineEdit()
        to_layout.addWidget(self.to_input)
        recipients_layout.addLayout(to_layout)
        
        cc_layout = QHBoxLayout()
        cc_layout.addWidget(QLabel("Cc:"))
        self.cc_input = QLineEdit()
        cc_layout.addWidget(self.cc_input)
        recipients_layout.addLayout(cc_layout)
        
        bcc_layout = QHBoxLayout()
        bcc_layout.addWidget(QLabel("Bcc:"))
        self.bcc_input = QLineEdit()
        bcc_layout.addWidget(self.bcc_input)
        recipients_layout.addLayout(bcc_layout)
        
        layout.addLayout(recipients_layout)
        
        subject_layout = QHBoxLayout()
        subject_layout.addWidget(QLabel("Subject:"))
        self.subject_input = QLineEdit()
        subject_layout.addWidget(self.subject_input)
        layout.addLayout(subject_layout)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        self.body_text = QTextEdit()
        layout.addWidget(self.body_text)
        
        attachments_layout = QVBoxLayout()
        attachments_layout.setContentsMargins(0, 0, 0, 0)
        attachments_layout.setSpacing(5)
        
        attachments_header = QHBoxLayout()
        attachments_header.addWidget(QLabel("Attachments:"))
        
        self.add_attachment_button = QPushButton("Add")
        self.add_attachment_button.clicked.connect(self.on_add_attachment_clicked)
        attachments_header.addWidget(self.add_attachment_button)
        
        attachments_layout.addLayout(attachments_header)
        
        self.attachments_container = QWidget()
        self.attachments_container.setLayout(QVBoxLayout())
        self.attachments_container.layout().setContentsMargins(0, 0, 0, 0)
        self.attachments_container.layout().setSpacing(5)
        attachments_layout.addWidget(self.attachments_container)
        
        layout.addLayout(attachments_layout)
    
    def set_reply_to(self, email: Email):
        """Set the email to reply to."""
        self.reply_to = email
        
        if not email:
            self.title_label.setText("New Email")
            self.to_input.setText("")
            self.cc_input.setText("")
            self.bcc_input.setText("")
            self.subject_input.setText("")
            self.body_text.setText("")
            return
        
        self.title_label.setText("Reply")
        
        if email.from_address:
            self.to_input.setText(email.from_address.address)
        
        if email.subject:
            if not email.subject.startswith("Re:"):
                self.subject_input.setText(f"Re: {email.subject}")
            else:
                self.subject_input.setText(email.subject)
        
        reply_text = f"\n\nOn {email.date.strftime('%Y-%m-%d %H:%M')}, {email.from_address.name if email.from_address and email.from_address.name else email.from_address.address if email.from_address else 'Unknown'} wrote:\n\n"
        
        if email.body_text:
            lines = email.body_text.split("\n")
            quoted_text = "\n".join([f"> {line}" for line in lines])
            reply_text += quoted_text
        
        self.body_text.setText(reply_text)
    
    def set_forward(self, email: Email):
        """Set the email to forward."""
        self.reply_to = email
        
        if not email:
            self.title_label.setText("New Email")
            self.to_input.setText("")
            self.cc_input.setText("")
            self.bcc_input.setText("")
            self.subject_input.setText("")
            self.body_text.setText("")
            return
        
        self.title_label.setText("Forward")
        
        if email.subject:
            if not email.subject.startswith("Fwd:"):
                self.subject_input.setText(f"Fwd: {email.subject}")
            else:
                self.subject_input.setText(email.subject)
        
        forward_text = f"\n\n---------- Forwarded message ----------\n"
        forward_text += f"From: {email.from_address.name if email.from_address and email.from_address.name else email.from_address.address if email.from_address else 'Unknown'}\n"
        
        if email.to_addresses:
            to_text = ", ".join([f"{addr.name} <{addr.address}>" if addr.name else addr.address 
                               for addr in email.to_addresses])
            forward_text += f"To: {to_text}\n"
        
        forward_text += f"Date: {email.date.strftime('%Y-%m-%d %H:%M')}\n"
        forward_text += f"Subject: {email.subject}\n\n"
        
        if email.body_text:
            forward_text += email.body_text
        
        self.body_text.setText(forward_text)
        
    
    def on_send_clicked(self):
        """Handle send button click."""
        to_addresses = self.parse_addresses(self.to_input.text())
        cc_addresses = self.parse_addresses(self.cc_input.text())
        bcc_addresses = self.parse_addresses(self.bcc_input.text())
        
        if not to_addresses:
            return
        
        from src.models.email import Email, EmailAddress, EmailImportance, EmailFlag, EmailFolder
        import uuid
        
        from_address = EmailAddress.create(address="user@example.com", name="User")
        
        email = Email.create(
            message_id=f"<{uuid.uuid4()}@localhost>",
            subject=self.subject_input.text(),
            from_address=from_address,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            bcc_addresses=bcc_addresses,
            body_text=self.body_text.toPlainText(),
            folder=EmailFolder.SENT,
        )
        
        self.send_clicked.emit(email)
    
    def on_cancel_clicked(self):
        """Handle cancel button click."""
        self.cancel_clicked.emit()
    
    def on_add_attachment_clicked(self):
        """Handle add attachment button click."""
        pass
    
    def parse_addresses(self, text: str) -> List[EmailAddress]:
        """Parse email addresses from text."""
        if not text:
            return []
        
        addresses = []
        
        for addr_str in text.split(","):
            addr_str = addr_str.strip()
            
            if not addr_str:
                continue
            
            import re
            match = re.match(r"(.*)<([^>]+)>", addr_str)
            
            if match:
                name = match.group(1).strip()
                email = match.group(2).strip()
                addresses.append(EmailAddress.create(address=email, name=name if name else None))
            else:
                addresses.append(EmailAddress.create(address=addr_str))
        
        return addresses


class EmailMainWidget(QWidget):
    """Main widget for email functionality."""
    
    def __init__(self, config: Config, email_connector: EmailConnectorService, 
                email_processor: EmailProcessorService, email_search: EmailSearchService, parent=None):
        """Initialize the email main widget."""
        super().__init__(parent)
        self.config = config
        self.email_connector = email_connector
        self.email_processor = email_processor
        self.email_search = email_search
        
        self.current_provider_id = None
        self.current_folder = EmailFolder.INBOX
        self.current_emails = []
        
        self.init_ui()
        
        subscribe_event(EventType.EMAILS_SYNCED, self.on_emails_synced)
        subscribe_event(EventType.EMAIL_PROCESSED, self.on_email_processed)
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        
        self.provider_combo = QComboBox()
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        toolbar.addWidget(self.provider_combo)
        
        self.sync_button = QPushButton("Sync")
        self.sync_button.clicked.connect(self.on_sync_clicked)
        toolbar.addWidget(self.sync_button)
        
        self.compose_button = QPushButton("Compose")
        self.compose_button.clicked.connect(self.on_compose_clicked)
        toolbar.addWidget(self.compose_button)
        
        layout.addWidget(toolbar)
        
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        self.folder_list = QListWidget()
        self.folder_list.setMaximumWidth(200)
        self.folder_list.currentRowChanged.connect(self.on_folder_changed)
        
        for folder in EmailFolder:
            if folder != EmailFolder.CUSTOM:
                self.folder_list.addItem(folder.name.capitalize())
        
        self.main_splitter.addWidget(self.folder_list)
        
        self.email_splitter = QSplitter(Qt.Horizontal)
        
        email_list_container = QWidget()
        email_list_layout = QVBoxLayout(email_list_container)
        email_list_layout.setContentsMargins(0, 0, 0, 0)
        email_list_layout.setSpacing(0)
        
        self.search_widget = EmailSearchWidget()
        self.search_widget.search_requested.connect(self.on_search_requested)
        email_list_layout.addWidget(self.search_widget)
        
        self.email_list = EmailListWidget()
        self.email_list.email_selected.connect(self.on_email_selected)
        email_list_layout.addWidget(self.email_list)
        
        self.email_splitter.addWidget(email_list_container)
        
        self.email_view = EmailViewWidget()
        self.email_view.reply_clicked.connect(self.on_reply_clicked)
        self.email_view.forward_clicked.connect(self.on_forward_clicked)
        self.email_view.delete_clicked.connect(self.on_delete_clicked)
        self.email_splitter.addWidget(self.email_view)
        
        self.email_compose = EmailComposeWidget()
        self.email_compose.send_clicked.connect(self.on_send_clicked)
        self.email_compose.cancel_clicked.connect(self.on_cancel_compose_clicked)
        self.email_compose.setVisible(False)
        self.email_splitter.addWidget(self.email_compose)
        
        self.main_splitter.addWidget(self.email_splitter)
        
        self.main_splitter.setSizes([200, 800])
        self.email_splitter.setSizes([300, 500])
        
        layout.addWidget(self.main_splitter)
        
        self.load_providers()
    
    def load_providers(self):
        """Load email providers."""
        self.provider_combo.clear()
        
        providers = self.config.get("email.providers", [])
        
        for provider in providers:
            provider_id = provider.get("id")
            provider_name = provider.get("name", provider_id)
            
            if provider_id:
                self.provider_combo.addItem(provider_name, provider_id)
        
        if self.provider_combo.count() > 0:
            self.provider_combo.setCurrentIndex(0)
    
    def on_provider_changed(self, index):
        """Handle provider change."""
        if index < 0:
            self.current_provider_id = None
            return
        
        provider_id = self.provider_combo.itemData(index)
        
        if provider_id == self.current_provider_id:
            return
        
        self.current_provider_id = provider_id
        
        asyncio.create_task(self.connect_provider())
    
    async def connect_provider(self):
        """Connect to the current provider."""
        if not self.current_provider_id:
            return
        
        success = await self.email_connector.connect(self.current_provider_id)
        
        if success:
            await self.email_connector.start_sync(self.current_provider_id)
            
            await self.load_emails()
    
    async def load_emails(self):
        """Load emails for the current folder."""
        if not self.current_provider_id:
            return
        
        emails = await self.email_connector.sync_emails(
            self.current_provider_id, 
            self.current_folder
        )
        
        self.current_emails = emails
        self.email_list.set_emails(emails)
    
    def on_sync_clicked(self):
        """Handle sync button click."""
        if self.current_provider_id:
            asyncio.create_task(self.load_emails())
    
    def on_folder_changed(self, row):
        """Handle folder change."""
        if row < 0:
            return
        
        folder_name = self.folder_list.item(row).text().upper()
        
        try:
            folder = EmailFolder[folder_name]
            
            if folder != self.current_folder:
                self.current_folder = folder
                
                asyncio.create_task(self.load_emails())
        except:
            pass
    
    def on_email_selected(self, email):
        """Handle email selection."""
        self.email_view.set_email(email)
        
        if email and not email.is_read:
            email.is_read = True
            
            for item in self.email_list.email_items:
                if item.email.id == email.id:
                    item.update_read_status()
    
    def on_search_requested(self, query):
        """Handle search request."""
        asyncio.create_task(self.search_emails(query))
    
    async def search_emails(self, query):
        """Search emails."""
        result = await self.email_search.search(query)
        
        self.current_emails = result.emails
        self.email_list.set_emails(result.emails)
    
    def on_compose_clicked(self):
        """Handle compose button click."""
        self.email_view.setVisible(False)
        self.email_compose.setVisible(True)
        self.email_compose.set_reply_to(None)
    
    def on_reply_clicked(self, email):
        """Handle reply button click."""
        self.email_view.setVisible(False)
        self.email_compose.setVisible(True)
        self.email_compose.set_reply_to(email)
    
    def on_forward_clicked(self, email):
        """Handle forward button click."""
        self.email_view.setVisible(False)
        self.email_compose.setVisible(True)
        self.email_compose.set_forward(email)
    
    def on_delete_clicked(self, email):
        """Handle delete button click."""
        pass
    
    def on_send_clicked(self, email):
        """Handle send button click."""
        if not self.current_provider_id:
            return
        
        asyncio.create_task(self.send_email(email))
    
    async def send_email(self, email):
        """Send an email."""
        success = await self.email_connector.send_email(self.current_provider_id, email)
        
        if success:
            self.email_compose.setVisible(False)
            self.email_view.setVisible(True)
            
            if self.current_folder == EmailFolder.SENT:
                await self.load_emails()
    
    def on_cancel_compose_clicked(self):
        """Handle cancel compose button click."""
        self.email_compose.setVisible(False)
        self.email_view.setVisible(True)
    
    def on_emails_synced(self, event_data):
        """Handle emails synced event."""
        provider_id = event_data.get("provider_id")
        folder = event_data.get("folder")
        
        if provider_id == self.current_provider_id and folder == self.current_folder.name:
            asyncio.create_task(self.load_emails())
    
    def on_email_processed(self, event_data):
        """Handle email processed event."""
        pass
