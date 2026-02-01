import { useChat } from '@livekit/components-react';
import { useRoomContext, useParticipants } from '@livekit/components-react';
import { MessageCircle } from 'lucide-react';
import { useEffect, useState } from 'react';

interface LiveTranscriptProps {
    className?: string;
}

interface TranscriptMessage {
    id: string;
    from: { identity: string; name?: string };
    message: string;
    timestamp: number;
    source: 'transcription' | 'chat';
    isFinal?: boolean;
}

const LiveTranscript: React.FC<LiveTranscriptProps> = ({ className = '' }) => {
    const { chatMessages } = useChat();
    const room = useRoomContext();
    const participants = useParticipants();
    const [allMessages, setAllMessages] = useState<TranscriptMessage[]>([]);
    const [transcriptionMessages, setTranscriptionMessages] = useState<TranscriptMessage[]>([]);

    // Register text stream handler for transcriptions
    useEffect(() => {
        if (!room) return;

        const handleTranscriptionStream = (reader: any, participantInfo: any) => {
            const participantIdentity = typeof participantInfo === 'string' ? participantInfo : participantInfo?.identity;
            console.log('[LiveTranscript] Received transcription stream from:', participantIdentity);

            const processStream = async () => {
                try {
                    const segmentId = reader.info?.attributes?.['lk.segment_id'] || Date.now().toString();
                    const messageId = `trans-${participantIdentity}-${segmentId}`;
                    let buffer = '';

                    const pushInterim = () => {
                        setTranscriptionMessages(prev => {
                            const existingIndex = prev.findIndex(m => m.id === messageId);
                            const nextMessage: TranscriptMessage = {
                                id: messageId,
                                from: {
                                    identity: participantIdentity,
                                    name: participants.find(p => p.identity === participantIdentity)?.name,
                                },
                                message: buffer,
                                timestamp: Date.now(),
                                source: 'transcription',
                                isFinal: false,
                            };

                            if (existingIndex >= 0) {
                                const updated = [...prev];
                                updated[existingIndex] = nextMessage;
                                return updated;
                            }

                            return [...prev, nextMessage];
                        });
                    };

                    if (reader && typeof reader.read === 'function') {
                        while (true) {
                            const chunk = await reader.read();
                            if (!chunk) break;
                            if (typeof chunk === 'string') {
                                buffer += chunk;
                            } else {
                                if (chunk.done) break;
                                if (chunk.value) {
                                    buffer += chunk.value;
                                }
                            }

                            if (buffer.length > 0) {
                                pushInterim();
                            }
                        }
                    } else if (reader && typeof reader[Symbol.asyncIterator] === 'function') {
                        for await (const chunk of reader as AsyncIterable<string>) {
                            if (chunk) {
                                buffer += chunk;
                                pushInterim();
                            }
                        }
                    } else if (reader && typeof reader.readAll === 'function') {
                        const text = await reader.readAll();
                        if (text) {
                            buffer = text;
                            pushInterim();
                        }
                    }

                    const isFinal = reader.info?.attributes?.['lk.transcription_final'] === 'true';
                    setTranscriptionMessages(prev => {
                        const existingIndex = prev.findIndex(m => m.id === messageId);
                        const nextMessage: TranscriptMessage = {
                            id: messageId,
                            from: {
                                identity: participantIdentity,
                                name: participants.find(p => p.identity === participantIdentity)?.name,
                            },
                            message: buffer,
                            timestamp: Date.now(),
                            source: 'transcription',
                            isFinal,
                        };

                        if (existingIndex >= 0) {
                            const updated = [...prev];
                            updated[existingIndex] = nextMessage;
                            return updated;
                        }

                        return [...prev, nextMessage];
                    });
                } catch (error) {
                    console.error('[LiveTranscript] Error reading transcription stream:', error);
                }
            };

            processStream();
        };

        try {
            room.registerTextStreamHandler('lk.transcription', handleTranscriptionStream);
            console.log('[LiveTranscript] Registered transcription handler');
        } catch (error: any) {
            // Silently ignore "already set" errors - handler is already registered
            if (!error?.message?.includes('already been set')) {
                console.error('[LiveTranscript] Error registering transcription handler:', error);
            }
        }

        return () => {
            // Cleanup if needed
        };
    }, [room, participants]);

    // Combine chat messages and transcriptions
    useEffect(() => {
        // Debug logging
        console.log('[LiveTranscript] Chat messages:', chatMessages.length);
        console.log('[LiveTranscript] Transcription messages:', transcriptionMessages.length);
        console.log('[LiveTranscript] Participants:', participants.length);

        const messages: TranscriptMessage[] = [];

        // Add transcriptions
        transcriptionMessages.forEach((trans) => {
            console.log('[LiveTranscript] Adding transcription:', {
                from: trans.from.identity,
                text: trans.message,
                isFinal: trans.isFinal,
            });
            messages.push(trans);
        });

        // Add chat messages
        chatMessages.forEach((msg) => {
            console.log('[LiveTranscript] Adding chat message:', {
                from: msg.from?.identity,
                text: msg.message,
            });

            messages.push({
                id: msg.id || `chat-${msg.timestamp}`,
                from: msg.from || { identity: 'unknown', name: 'Unknown' },
                message: msg.message,
                timestamp: msg.timestamp,
                source: 'chat',
            });
        });

        // Sort by timestamp
        messages.sort((a, b) => a.timestamp - b.timestamp);
        console.log('[LiveTranscript] Total messages:', messages.length);
        setAllMessages(messages);
    }, [chatMessages, transcriptionMessages, participants]);
    const getAvatarColor = (identity: string): string => {
        const colors = [
            'bg-blue-500',
            'bg-purple-500',
            'bg-pink-500',
            'bg-green-500',
            'bg-yellow-500',
            'bg-red-500',
            'bg-indigo-500',
            'bg-cyan-500'
        ];
        // Use identity hash to consistently assign colors
        const hash = identity.split('').reduce((acc, char) => {
            return acc + char.charCodeAt(0);
        }, 0);
        return colors[hash % colors.length];
    };

    // Get initials from name/identity
    const getInitials = (identity: string): string => {
        const parts = identity.split('-');
        if (parts.length >= 2) {
            return (parts[0].charAt(0) + parts[1].charAt(0)).toUpperCase();
        }
        return identity.substring(0, 2).toUpperCase();
    };

    // Format timestamp
    const formatTime = (timestamp: number): string => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    // Determine if message is from local participant
    const isLocalMessage = (fromIdentity: string): boolean => {
        return room?.localParticipant?.identity === fromIdentity;
    };

    // Auto-scroll effect
    useEffect(() => {
        const scrollContainer = document.getElementById('transcript-scroll');
        if (scrollContainer) {
            scrollContainer.scrollTop = scrollContainer.scrollHeight;
        }
    }, [allMessages]);

    if (allMessages.length === 0) {
        return (
            <div className={`flex flex-col items-center justify-center h-full text-gray-400 ${className}`}>
                <MessageCircle className="w-10 h-10 sm:w-12 sm:h-12 mb-3 sm:mb-4 opacity-50" />
                <p className="text-xs sm:text-sm font-medium">Waiting for conversation...</p>
                <p className="text-[10px] sm:text-xs mt-2 text-gray-400">Messages will appear here</p>
            </div>
        );
    }

    return (
        <div className={`flex flex-col h-full ${className}`}>
            <div id="transcript-scroll" className="flex-1 overflow-y-auto space-y-2 sm:space-y-3 p-3 sm:p-5 scrollbar-thin">
                {allMessages.map((msg, index) => {
                    const isLocal = isLocalMessage(msg.from.identity);
                    const displayName = msg.from?.name || msg.from.identity || 'Unknown';
                    const avatarColor = getAvatarColor(msg.from.identity);
                    const initials = getInitials(displayName);
                    const isTranscription = msg.source === 'transcription';

                    return (
                        <div
                            key={msg.id || index}
                            className={`flex gap-1.5 sm:gap-2 ${isLocal ? 'justify-end' : 'justify-start'} animate-fadeIn`}
                        >
                            {!isLocal && (
                                <div
                                    className={`w-6 h-6 sm:w-7 sm:h-7 rounded-full ${avatarColor} flex items-center justify-center flex-shrink-0 text-white text-[10px] sm:text-xs font-semibold shadow-sm`}
                                    title={displayName}
                                >
                                    {initials}
                                </div>
                            )}

                            <div className={`flex flex-col ${isLocal ? 'items-end' : 'items-start'} max-w-[75%] sm:max-w-[70%]`}>
                                <div
                                    className={`px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-2xl text-xs sm:text-sm break-words shadow-sm ${isLocal
                                        ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-br-sm'
                                        : 'bg-white text-gray-900 rounded-bl-sm border border-gray-100'
                                        } ${isTranscription && !msg.isFinal ? 'opacity-60 italic' : ''
                                        }`}
                                >
                                    {msg.message}
                                </div>

                                <div className="text-[9px] sm:text-[10px] text-gray-400 mt-1 px-1">
                                    {formatTime(msg.timestamp)}
                                </div>
                            </div>

                            {isLocal && (
                                <div
                                    className={`w-6 h-6 sm:w-7 sm:h-7 rounded-full ${avatarColor} flex items-center justify-center flex-shrink-0 text-white text-[10px] sm:text-xs font-semibold shadow-sm`}
                                    title={displayName}
                                >
                                    {initials}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default LiveTranscript;
