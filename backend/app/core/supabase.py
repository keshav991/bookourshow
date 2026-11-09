from supabase import create_client, Client
from app.core.config import settings

# Initialize Supabase client with publishable key
supabase_client: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_PUBLISHABLE_KEY
)


def get_supabase_client() -> Client:
    """Return the initialized Supabase client singleton."""
    return supabase_client
