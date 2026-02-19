import React, { Component } from 'react';

export default class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, info) {
        console.error('CourtVision crashed:', error, info);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{ padding: 40, color: '#FF4444', fontFamily: 'monospace' }}>
                    <h2>RENDER ERROR</h2>
                    <pre style={{ whiteSpace: 'pre-wrap', color: '#aaa', fontSize: 12 }}>
                        {this.state.error?.toString()}
                        {'\n'}
                        {this.state.error?.stack}
                    </pre>
                </div>
            );
        }
        return this.props.children;
    }
}
