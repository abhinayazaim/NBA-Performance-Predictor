import { useQuery } from '@tanstack/react-query';
import {
    fetchPlayers,
    fetchPlayerProfile,
    fetchPlayerPrediction,
    fetchPlayerCareer,
    fetchPlayerIntel
} from '../api';

export const usePlayers = () => {
    return useQuery({
        queryKey: ['players'],
        queryFn: fetchPlayers,
        staleTime: 1000 * 60 * 60 * 24, // 24 hours
    });
};

export const usePlayerProfile = (playerId) => {
    return useQuery({
        queryKey: ['profile', playerId],
        queryFn: () => fetchPlayerProfile(playerId),
        enabled: !!playerId,
        staleTime: 1000 * 60 * 15,
        gcTime: 1000 * 60 * 60,
        placeholderData: (prev) => prev,
    });
};

export const usePlayerPrediction = (playerId) => {
    return useQuery({
        queryKey: ['prediction', playerId],
        queryFn: () => fetchPlayerPrediction(playerId),
        enabled: !!playerId,
        staleTime: 1000 * 60 * 5,
        gcTime: 1000 * 60 * 30,
        placeholderData: (prev) => prev,
    });
};

export const usePlayerCareer = (playerId) => {
    return useQuery({
        queryKey: ['career', playerId],
        queryFn: () => fetchPlayerCareer(playerId),
        enabled: !!playerId,
        staleTime: 1000 * 60 * 60, // 1 hour
    });
};

export const usePlayerIntel = (playerId) => {
    return useQuery({
        queryKey: ['intel', playerId],
        queryFn: () => fetchPlayerIntel(playerId),
        enabled: !!playerId,
        staleTime: 1000 * 60 * 60 * 24,
        gcTime: 1000 * 60 * 60 * 48,
        placeholderData: (prev) => prev,
    });
};
