import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Info } from 'lucide-react';
import { ROUTES } from '../config/constants';
import { createSession, handleApiError } from '../lib/api';
import { AnimatedOrb } from '../components/AnimatedOrb';

function ChooseAvatarPage() {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const startSession = async (useAvatar: boolean) => {
        setIsLoading(true);
        setError(null);

        try {
            const session = await createSession(undefined, useAvatar);
            navigate(ROUTES.SESSION, {
                state: {
                    token: session.token,
                    url: session.url,
                    roomName: session.roomName,
                    participantName: session.participantName,
                    useAvatar,
                },
            });
        } catch (err) {
            console.error('Error creating session:', err);
            setError(handleApiError(err));
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-white flex items-center justify-center p-6 relative overflow-hidden">
            <div className="absolute left-6 top-6">
                <button
                    type="button"
                    onClick={() => navigate(ROUTES.HOME)}
                    className="text-sm text-gray-500 hover:text-gray-700"
                >
                    ← Back
                </button>
            </div>

            <div className="relative z-10 w-full max-w-4xl">
                <div className="flex flex-col items-center text-center mb-10">
                    <AnimatedOrb size={180} />
                    <h1 className="mt-6 text-3xl font-semibold text-gray-900">Choose your experience</h1>
                    <p className="mt-2 text-sm text-gray-500">
                        You can start immediately without an avatar or wait for the avatar to load.
                    </p>
                </div>

                <div className="grid gap-6 md:grid-cols-2">
                    <button
                        type="button"
                        disabled={isLoading}
                        onClick={() => startSession(false)}
                        className="text-left rounded-2xl border border-gray-200 bg-white shadow-sm hover:shadow-md transition-all p-6 disabled:opacity-60"
                    >
                        <div className="flex items-start justify-between">
                            <div>
                                <h2 className="text-lg font-semibold text-gray-900">Without avatar</h2>
                                <p className="mt-2 text-sm text-gray-600">
                                    Start the conversation instantly with voice only.
                                </p>
                            </div>
                            <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center text-green-600">
                                <span className="text-sm font-semibold">0s</span>
                            </div>
                        </div>
                        <div className="mt-6 inline-flex items-center text-sm font-medium text-blue-600">
                            Start now
                        </div>
                    </button>

                    <button
                        type="button"
                        disabled={isLoading}
                        onClick={() => startSession(true)}
                        className="text-left rounded-2xl border border-gray-200 bg-white shadow-sm hover:shadow-md transition-all p-6 disabled:opacity-60"
                    >
                        <div className="flex items-start justify-between">
                            <div>
                                <div className="flex items-center gap-2">
                                    <h2 className="text-lg font-semibold text-gray-900">With avatar</h2>
                                    <Info className="w-4 h-4 text-gray-400" />
                                </div>
                                <p className="mt-2 text-sm text-gray-600">
                                    Hyper‑realistic avatar. Average load time ~30 seconds.
                                </p>
                            </div>
                            <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center text-amber-700">
                                <span className="text-sm font-semibold">~30s</span>
                            </div>
                        </div>
                        <div className="mt-6 inline-flex items-center text-sm font-medium text-blue-600">
                            Start with avatar
                        </div>
                    </button>
                </div>

                {error && (
                    <div className="mt-8 p-4 bg-red-500/20 border border-red-400/50 text-red-800 rounded-xl max-w-2xl mx-auto">
                        {error}
                    </div>
                )}
            </div>
        </div>
    );
}

export default ChooseAvatarPage;
