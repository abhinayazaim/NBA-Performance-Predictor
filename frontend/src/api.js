import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8008/api';

export const fetchPlayers = async () => {
    const response = await axios.get(`${API_BASE_URL}/players`);
    return response.data;
};

export const fetchPlayerProfile = async (playerId) => {
    if (!playerId) return null;
    const response = await axios.get(`${API_BASE_URL}/player/${playerId}/profile`);
    return response.data;
};

export const fetchPlayerPrediction = async (playerId) => {
    if (!playerId) return null;
    const response = await axios.get(`${API_BASE_URL}/player/${playerId}/predict`);
    return response.data;
};

export const fetchPlayerCareer = async (playerId) => {
    if (!playerId) return null;
    const response = await axios.get(`${API_BASE_URL}/player/${playerId}/career`);
    return response.data;
};

export const fetchPlayerIntel = async (playerId) => {
    if (!playerId) return null;
    const response = await axios.get(`${API_BASE_URL}/player/${playerId}/intel`);
    return response.data;
};
