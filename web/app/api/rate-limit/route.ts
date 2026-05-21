import { NextResponse } from 'next/server';

// In-memory rate limiting - survives for the duration of the serverless function
const userCounts = new Map<string, number>();
const userFirstCharacter = new Map<string, string>();

export async function POST(req: Request) {
  try {
    const { userEmail, characterId, action } = await req.json();
    
    if (!userEmail || userEmail === 'samarthpasalkar4@gmail.com') {
      return NextResponse.json({ allowed: true, count: 0, reason: 'admin' });
    }

    const currentCount = userCounts.get(userEmail) || 0;
    
    if (action === 'check') {
      // Check if user is blocked
      if (currentCount >= 2) {
        return NextResponse.json({ 
          allowed: false, 
          count: currentCount, 
          reason: 'rate_limit_exceeded',
          message: 'You have used your 2 free interactions. Please share feedback!'
        });
      }

      // Check character locking
      const lockedCharacter = userFirstCharacter.get(userEmail);
      if (lockedCharacter && lockedCharacter !== characterId) {
        return NextResponse.json({
          allowed: false,
          count: currentCount,
          reason: 'character_locked',
          lockedCharacter,
          message: `You can only interact with ${lockedCharacter}. Please go back and select that character.`
        });
      }

      return NextResponse.json({ 
        allowed: true, 
        count: currentCount,
        nextCount: currentCount + 1,
        reason: 'allowed' 
      });
    }

    if (action === 'increment') {
      // Increment user count and set character lock
      const newCount = currentCount + 1;
      userCounts.set(userEmail, newCount);
      
      if (!userFirstCharacter.has(userEmail)) {
        userFirstCharacter.set(userEmail, characterId);
      }

      return NextResponse.json({ 
        success: true, 
        newCount,
        lockedCharacter: userFirstCharacter.get(userEmail)
      });
    }

    if (action === 'reset') {
      // Reset user (for testing)
      userCounts.delete(userEmail);
      userFirstCharacter.delete(userEmail);
      return NextResponse.json({ success: true, message: 'User reset' });
    }

    if (action === 'debug') {
      // Debug info
      return NextResponse.json({
        userEmail,
        count: currentCount,
        lockedCharacter: userFirstCharacter.get(userEmail),
        allUsers: Object.fromEntries(userCounts),
        allCharacters: Object.fromEntries(userFirstCharacter)
      });
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });

  } catch (error) {
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
}