import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the scope for the Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'

def get_sheets_service():
    """
    Authenticates with the Google Sheets API using a service account
    and returns a service object.
    """
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            "The 'credentials.json' file was not found. "
            "Please follow the instructions to create it and place it in the root directory."
        )

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    service = build('sheets', 'v4', credentials=creds)
    return service

# --- Placeholder functions to be implemented later ---

def read_sheet(spreadsheet_id, range_name):
    """
    Reads data from a Google Sheet.
    Returns a tuple: (values, error_message).
    """
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        return values, None
    except HttpError as e:
        error_message = f"Google Sheets API Error: {e.reason} (Code: {e.status_code})"
        if e.status_code == 404:
            error_message = "Spreadsheet not found. Please check the Spreadsheet ID."
        elif e.status_code == 403:
            error_message = "Permission denied. Make sure the service account has access to the sheet."
        print(error_message)
        return None, error_message
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, "An unexpected error occurred while reading the sheet."

def write_to_sheet(spreadsheet_id, values):
    """
    Writes data to a Google Sheet.
    Returns a tuple: (success, error_message).
    """
    try:
        service = get_sheets_service()
        body = {'values': values}
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range='A1',
            valueInputOption='USER_ENTERED', body=body).execute()
        print(f"{result.get('updatedCells')} cells updated.")
        return True, None
    except HttpError as e:
        error_message = f"Google Sheets API Error: {e.reason} (Code: {e.status_code})"
        print(error_message)
        return False, error_message
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False, "An unexpected error occurred while writing to the sheet."

def create_new_sheet(title):
    """
    Creates a new Google Sheet.
    Returns a tuple: (spreadsheet_id, spreadsheet_url, error_message).
    """
    try:
        service = get_sheets_service()
        spreadsheet = {'properties': {'title': title}}
        spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId,spreadsheetUrl').execute()
        return spreadsheet.get('spreadsheetId'), spreadsheet.get('spreadsheetUrl'), None
    except HttpError as e:
        error_message = f"Google Sheets API Error: {e.reason} (Code: {e.status_code})"
        print(error_message)
        return None, None, error_message
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None, "An unexpected error occurred while creating the sheet."