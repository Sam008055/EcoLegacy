import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const userEmail = searchParams.get('email');
    
    if (!userEmail) {
      return NextResponse.json({ error: 'Email parameter required' }, { status: 400 });
    }

    const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Get all conversations for this user
    const { data: conversations, error } = await supabase
      .from('conversations')
      .select('*')
      .eq('session_id', userEmail)
      .order('created_at', { ascending: true });

    if (error) {
      return NextResponse.json({ 
        error: 'Database error', 
        details: error,
        userEmail 
      }, { status: 500 });
    }

    return NextResponse.json({
      userEmail,
      conversationCount: conversations?.length || 0,
      conversations: conversations || [],
      rateLimitStatus: conversations?.length >= 2 ? 'BLOCKED' : 'ALLOWED',
      remainingConversations: Math.max(0, 2 - (conversations?.length || 0))
    });

  } catch (error) {
    return NextResponse.json({ 
      error: 'Server error', 
      details: error 
    }, { status: 500 });
  }
}