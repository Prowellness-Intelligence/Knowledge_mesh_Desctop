# Knowledge Mesh Desktop User Guide

This document provides a comprehensive guide for using the Knowledge Mesh Desktop application, including installation, configuration, and day-to-day usage.

## Table of Contents

1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Managing Documents](#managing-documents)
4. [Exploring Relationships](#exploring-relationships)
5. [Searching](#searching)
6. [Configuring Settings](#configuring-settings)
7. [Using Proactive Assistance](#using-proactive-assistance)
8. [Integration with Calendar and Email](#integration-with-calendar-and-email)
9. [Voice Interaction](#voice-interaction)
10. [Troubleshooting](#troubleshooting)

## Installation

### System Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+ recommended)
- **Processor**: Intel Core i5 or equivalent (i7 recommended for large document collections)
- **Memory**: 8GB RAM minimum (16GB recommended)
- **Storage**: 1GB for the application + storage for your documents
- **Python**: 3.10 or higher

### Installation Steps

1. **Download the Application**

   Download the latest release from the official website or GitHub repository.

2. **Install Python Dependencies**

   ```bash
   # Create a virtual environment
   python -m venv venv
   
   # Activate the virtual environment
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Run the Application**

   ```bash
   python -m src.core.app
   ```

## Getting Started

### First Launch

When you first launch the application, you'll be greeted with a welcome screen that guides you through the initial setup:

1. **Select Directories to Monitor**: Choose which directories you want the application to monitor for documents.
2. **Configure Document Types**: Select which document types you want to process.
3. **Set Privacy Preferences**: Configure how proactive the assistant should be and what data it can access.

### Main Interface

The main interface consists of several panels:

- **Document Panel**: Displays your documents and allows you to manage them.
- **Relationship Panel**: Shows relationships between documents.
- **Search Panel**: Allows you to search across your documents and relationships.
- **Settings Panel**: Provides access to application settings.
- **Notification Panel**: Displays proactive notifications.

## Managing Documents

### Adding Documents

Documents can be added to the system in several ways:

1. **Automatic Detection**: The file monitor service will automatically detect new documents in the monitored directories.
2. **Manual Addition**: Click the "Add Document" button in the Document Panel to manually add a document.
3. **Drag and Drop**: Drag a document from your file explorer and drop it into the Document Panel.

### Viewing Documents

To view a document:

1. Select the document in the Document Panel.
2. The document content will be displayed in the main view.
3. Document metadata and summary will be displayed in the sidebar.

### Editing Document Metadata

To edit document metadata:

1. Select the document in the Document Panel.
2. Click the "Edit" button in the document view.
3. Modify the metadata fields as needed.
4. Click "Save" to save your changes.

### Deleting Documents

To delete a document:

1. Select the document in the Document Panel.
2. Click the "Delete" button in the document view.
3. Confirm the deletion when prompted.

## Exploring Relationships

### Viewing Relationships

The Relationship Panel shows the relationships between documents in two views:

1. **List View**: Displays relationships as a list, sorted by strength or creation date.
2. **Graph View**: Displays relationships as a graph, with documents as nodes and relationships as edges.

To view a relationship:

1. Select the relationship in the list view or click on an edge in the graph view.
2. The relationship details will be displayed in the sidebar.

### Creating Relationships

Relationships are typically discovered automatically by the Knowledge Mesh Service, but you can also create them manually:

1. Select a document in the Document Panel.
2. Click the "Create Relationship" button.
3. Select the target document.
4. Choose the relationship type.
5. Set the relationship strength.
6. Add any additional metadata.
7. Click "Create" to create the relationship.

### Editing Relationships

To edit a relationship:

1. Select the relationship in the Relationship Panel.
2. Click the "Edit" button in the relationship view.
3. Modify the relationship properties as needed.
4. Click "Save" to save your changes.

### Deleting Relationships

To delete a relationship:

1. Select the relationship in the Relationship Panel.
2. Click the "Delete" button in the relationship view.
3. Confirm the deletion when prompted.

## Searching

### Basic Search

To perform a basic search:

1. Enter your search query in the search box in the Search Panel.
2. Select the search type (All, Documents, Relationships).
3. Click the "Search" button or press Enter.
4. View the search results in the results list.

### Advanced Search

For more advanced searches:

1. Click the "Advanced" button in the Search Panel.
2. Configure the search parameters:
   - **Document Types**: Filter by document type.
   - **Date Range**: Filter by creation or modification date.
   - **Metadata**: Filter by document metadata.
   - **Relationship Types**: Filter by relationship type.
   - **Relationship Strength**: Filter by relationship strength.
3. Click "Search" to perform the search.

### Saving Searches

To save a search for future use:

1. Perform a search.
2. Click the "Save" button in the Search Panel.
3. Enter a name for the search.
4. Click "Save" to save the search.

To use a saved search:

1. Click the "Saved Searches" button in the Search Panel.
2. Select a saved search from the list.
3. The search will be performed automatically.

## Configuring Settings

### General Settings

The Settings Panel allows you to configure various aspects of the application:

1. **General Settings**:
   - Application name
   - Data directory
   - Log level
   - Theme
   - Font size

2. **File Monitor Settings**:
   - Directories to monitor
   - File extensions to process
   - Recursive monitoring
   - Ignore patterns
   - Polling interval

3. **Document Processor Settings**:
   - Chunk size
   - Chunk overlap
   - Extract metadata
   - Generate summaries
   - Summary length
   - OCR settings

4. **Knowledge Mesh Settings**:
   - Embedding model
   - Similarity threshold
   - Minimum relationship strength
   - Auto-detect relationships
   - Relationship types
   - Maximum relationships

5. **Proactive Settings**:
   - Enable/disable proactive assistance
   - Minimum interaction interval
   - Maximum daily interactions
   - Interaction types
   - Work pattern learning
   - Privacy level
   - Notification style

6. **UI Settings**:
   - Theme
   - Font family
   - Font size
   - Window size
   - Show welcome screen

### Importing and Exporting Settings

To export your settings:

1. Go to the Settings Panel.
2. Click the "Export" button.
3. Choose a location to save the settings file.
4. Click "Save" to export the settings.

To import settings:

1. Go to the Settings Panel.
2. Click the "Import" button.
3. Select a settings file.
4. Click "Open" to import the settings.

## Using Proactive Assistance

### Proactive Notifications

The Proactive Service monitors your work patterns and provides suggestions and insights based on your behavior. Notifications appear in the Notification Panel and can include:

1. **Document Suggestions**: Recommendations for documents that might be relevant to your current task.
2. **Relationship Suggestions**: Suggestions for relationships between documents that you might not have noticed.
3. **Work Pattern Insights**: Insights about your work patterns and productivity.

### Configuring Proactive Assistance

To configure proactive assistance:

1. Go to the Settings Panel.
2. Navigate to the Proactive Settings tab.
3. Configure the settings as needed:
   - **Enable/Disable**: Turn proactive assistance on or off.
   - **Interaction Interval**: Set the minimum time between interactions.
   - **Daily Limit**: Set the maximum number of interactions per day.
   - **Interaction Types**: Choose which types of interactions to receive.
   - **Privacy Level**: Set the level of privacy for proactive assistance.
   - **Notification Style**: Choose how notifications are displayed.

### Responding to Notifications

When you receive a notification, you can:

1. **Open**: Click the action button to open the suggested document or relationship.
2. **Dismiss**: Click the "Close" button to dismiss the notification.
3. **Snooze**: Click the "Snooze" button to hide the notification temporarily.
4. **Disable**: Click the "Don't show again" button to disable this type of notification.

## Integration with Calendar and Email

### Calendar Integration

The Calendar Service integrates with your calendar applications to connect meetings with relevant documents:

1. **Enabling Calendar Integration**:
   - Go to the Settings Panel.
   - Navigate to the Calendar Settings tab.
   - Enable calendar integration.
   - Configure the calendar providers.

2. **Viewing Calendar Events**:
   - Go to the Calendar Panel.
   - View upcoming events.
   - Click on an event to see related documents.

3. **Finding Documents for Events**:
   - Select an event in the Calendar Panel.
   - Click "Find Related Documents" to see documents that might be relevant to the event.

### Email Integration

The Email Service processes emails and attachments:

1. **Enabling Email Integration**:
   - Go to the Settings Panel.
   - Navigate to the Email Settings tab.
   - Enable email integration.
   - Configure the email providers.

2. **Viewing Emails**:
   - Go to the Email Panel.
   - View recent emails.
   - Click on an email to see its content and attachments.

3. **Processing Attachments**:
   - Select an email with attachments.
   - Click "Process Attachments" to extract documents from the attachments.

## Voice Interaction

### Enabling Voice Interaction

The Voice Service enables voice interaction with the application:

1. **Enabling Voice Interaction**:
   - Go to the Settings Panel.
   - Navigate to the Voice Settings tab.
   - Enable voice interaction.
   - Configure the voice settings.

2. **Using Voice Commands**:
   - Say the wake word (default: "assistant") to activate voice interaction.
   - Speak a command.
   - The application will respond with voice and/or visual feedback.

### Common Voice Commands

Here are some common voice commands:

- "Open document [document name]"
- "Search for [query]"
- "Show relationships for [document name]"
- "Create a new document"
- "What's on my calendar today?"
- "Show me my recent emails"
- "What are you suggesting?"
- "Configure settings"

## Troubleshooting

### Common Issues

#### Application Won't Start

- Check that Python 3.10 or higher is installed.
- Verify that all dependencies are installed.
- Check the log file for error messages.

#### Documents Not Being Detected

- Verify that the directories are being monitored.
- Check that the file extensions are configured correctly.
- Ensure that the file monitor service is running.

#### Search Not Working

- Verify that the vector store service is running.
- Check that documents have been processed and indexed.
- Try rebuilding the vector index.

#### Proactive Assistance Not Working

- Verify that proactive assistance is enabled.
- Check the privacy level settings.
- Ensure that work pattern learning is enabled.

#### Voice Interaction Not Working

- Verify that voice interaction is enabled.
- Check that your microphone is working.
- Try adjusting the voice settings.

### Log Files

Log files are stored in the data directory and can be useful for troubleshooting:

- **Application Log**: `~/.knowledge_mesh/logs/app.log`
- **File Monitor Log**: `~/.knowledge_mesh/logs/file_monitor.log`
- **Document Processor Log**: `~/.knowledge_mesh/logs/document_processor.log`
- **Knowledge Mesh Log**: `~/.knowledge_mesh/logs/knowledge_mesh.log`
- **Proactive Service Log**: `~/.knowledge_mesh/logs/proactive.log`

### Getting Help

If you encounter issues that you can't resolve:

1. Check the documentation for solutions.
2. Search the GitHub repository for similar issues.
3. Submit a bug report with detailed information about the issue.
4. Contact support for assistance.

## Advanced Topics

### Customizing the Application

The application is designed to be easily extended and customized:

1. **Custom Document Processors**:
   - Create a new document processor in the `src/services/document_processor` directory.
   - Implement the required interface.
   - Register the processor in the document processor service.

2. **Custom Relationship Types**:
   - Add a new relationship type to the `RelationshipType` enum.
   - Implement a discovery method in the knowledge mesh service.
   - Update the configuration to include the new relationship type.

3. **Custom UI Components**:
   - Create a new UI component in the `src/ui` directory.
   - Implement the required interface.
   - Add the component to the main window.

### Backup and Restore

To backup your data:

1. Go to the Settings Panel.
2. Click the "Backup" button.
3. Choose a location to save the backup file.
4. Click "Save" to create the backup.

To restore from a backup:

1. Go to the Settings Panel.
2. Click the "Restore" button.
3. Select a backup file.
4. Click "Open" to restore from the backup.

### Performance Optimization

For large document collections, consider these performance optimizations:

1. **Limit Monitored Directories**: Monitor only the directories that contain important documents.
2. **Filter File Types**: Process only the file types that are relevant to your work.
3. **Adjust Chunk Size**: Increase the chunk size to reduce the number of chunks.
4. **Disable Features**: Disable features that you don't use, such as OCR or summary generation.
5. **Upgrade Hardware**: Consider upgrading your hardware, especially RAM and storage.

## Keyboard Shortcuts

The application supports various keyboard shortcuts for common actions:

- **Ctrl+O**: Open document
- **Ctrl+N**: New document
- **Ctrl+F**: Search
- **Ctrl+S**: Save
- **Ctrl+P**: Print
- **Ctrl+,**: Open settings
- **Ctrl+H**: Show/hide sidebar
- **Ctrl+Tab**: Switch between panels
- **F1**: Show help
- **Esc**: Close dialog or cancel operation
