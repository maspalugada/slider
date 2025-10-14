import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
    Returns a list of lists containing the cell values.
    """
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        return values
    except Exception as e:
        print(f"An error occurred while reading the sheet: {e}")
        return None

def write_to_sheet(spreadsheet_id, values):
    """
    Writes data to a Google Sheet.
    Assumes writing starts from the first cell (A1).
    """
    try:
        service = get_sheets_service()
        body = {
            'values': values
        }
        # The range is not specified here, so it defaults to the sheet's dimensions
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range='A1',
            valueInputOption='USER_ENTERED', body=body).execute()
        print(f"{result.get('updatedCells')} cells updated.")
        return True
    except Exception as e:
        print(f"An error occurred while writing to the sheet: {e}")
        return False

def create_new_sheet(title):
    """
    Creates a new Google Sheet and returns its ID and URL.
    """
    try:
        service = get_sheets_service()
        spreadsheet = {
            'properties': {
                'title': title
            }
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId,spreadsheetUrl').execute()
        return spreadsheet.get('spreadsheetId'), spreadsheet.get('spreadsheetUrl')
    except Exception as e:
        print(f"An error occurred while creating the sheet: {e}")
        return None, None