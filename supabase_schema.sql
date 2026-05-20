-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- Create the main corpus table to store texts and their embeddings
-- We keep the name 'osho_corpus' for backward compatibility, but it now stores all characters
create table if not exists osho_corpus (
  id uuid primary key default gen_random_uuid(),
  character_id text default 'osho',
  content text not null,
  source text,
  chapter text,
  embedding vector(768),
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Note: If the table already exists, run this to add the column:
-- alter table osho_corpus add column if not exists character_id text default 'osho';

-- Create a function to similarity search for documents
create or replace function match_documents(
  query_embedding vector(768),
  match_threshold float default 0.7,
  match_count int default 5,
  p_character_id text default null
)
returns table (
  id uuid,
  content text,
  source text,
  similarity float
)
language sql stable
as $$
  select
    id,
    content,
    source,
    1 - (embedding <=> query_embedding) as similarity
  from osho_corpus
  where 1 - (embedding <=> query_embedding) > match_threshold
    and (p_character_id is null or character_id = p_character_id)
  order by similarity desc
  limit match_count;
$$;

-- Create the conversations table to log user interactions
create table if not exists conversations (
  id uuid primary key default gen_random_uuid(),
  session_id text,
  character_id text,
  user_message text,
  avatar_response text,
  audio_url text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS on conversations (service role key bypasses RLS)
alter table conversations enable row level security;

-- Allow authenticated users to view their own conversations
drop policy if exists "Users can view own conversations" on conversations;
create policy "Users can view own conversations"
  on conversations for select
  to authenticated
  using (true);

-- Allow inserts via service role (RLS bypassed) or authenticated users
drop policy if exists "Users can insert conversations" on conversations;
create policy "Users can insert conversations"
  on conversations for insert
  to authenticated
  with check (true);

-- Index for fast rate limiting lookups
create index if not exists idx_conversations_session on conversations(session_id);

-- Create the feedback table to store user ratings and comments
create table if not exists feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id),
  character_id text,
  user_email text,
  rating int not null,
  comment text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security on feedback
alter table feedback enable row level security;

-- Allow authenticated users to insert their own feedback
drop policy if exists "Users can insert own feedback" on feedback;
create policy "Users can insert own feedback"
  on feedback for insert
  to authenticated
  with check (auth.uid() = user_id);

-- Allow authenticated users to view all feedback (useful for the feedback dashboard page)
drop policy if exists "Users can view all feedback" on feedback;
create policy "Users can view all feedback"
  on feedback for select
  to authenticated
  using (true);

-- Create a table for caching TTS and LLM responses for quick questions
create table if not exists cached_responses (
  id uuid primary key default gen_random_uuid(),
  character_id text not null,
  question text not null,
  answer_text text not null,
  audio_url text, -- Made nullable since we might not always have audio
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  unique(character_id, question)
);

-- Allow authenticated users to select from cache
alter table cached_responses enable row level security;

drop policy if exists "Users can view cached responses" on cached_responses;
create policy "Users can view cached responses"
  on cached_responses for select
  to authenticated
  using (true);

-- Allow authenticated users to insert to cache
drop policy if exists "Users can insert cached responses" on cached_responses;
create policy "Users can insert cached responses"
  on cached_responses for insert
  to authenticated
  with check (true);

-- Create audio cache table for TTS responses
create table if not exists audio_cache (
  id uuid primary key default gen_random_uuid(),
  cache_key text not null unique,
  character_id text not null,
  text text not null,
  audio_url text not null,
  successful_token_index int,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS on audio cache
alter table audio_cache enable row level security;

-- Allow authenticated users to select from audio cache
drop policy if exists "Users can view audio cache" on audio_cache;
create policy "Users can view audio cache"
  on audio_cache for select
  to authenticated
  using (true);

-- Allow authenticated users to insert to audio cache
drop policy if exists "Users can insert audio cache" on audio_cache;
create policy "Users can insert audio cache"
  on audio_cache for insert
  to authenticated
  with check (true);

-- Create index for faster cache lookups
create index if not exists idx_audio_cache_key on audio_cache(cache_key);
create index if not exists idx_cached_responses_lookup on cached_responses(character_id, question);