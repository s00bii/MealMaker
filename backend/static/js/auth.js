const SUPABASE_URL = "https://ttecrjtzqptstaqiztia.supabase.co"
const SUPABASE_ANON_KEY = "sb_publishable_cHHxBu6RwUCWJPQyWKqc7g_au4AtKsJ"

const { createClient } = supabase;
const supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function getSession() {
    const { data: { session } } = await supabaseClient.auth.getSession();
    return session;
}

async function getToken() {
    const session = await getSession();
    return session?.access_token || null;
}

async function requireLogin() {
    const session = await getSession();
    if (!session) {
        window.location.href = "/login";
    }
    return session;
}

async function logout() {
    await supabaseClient.auth.signOut();
    window.location.href = "/login";
}

async function apiFetch(path, options = {}) {
    const token = await getToken();
    return fetch(path, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(options.headers ?? {}),
        },
    });
}

async function redirectIfAuthed() {
    const session = await getSession();
    if (session) window.location.href = "/";
}