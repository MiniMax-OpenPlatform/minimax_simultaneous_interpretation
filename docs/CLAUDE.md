# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains API documentation and example code for working with AI services:

- **t2a.txt**: Text-to-speech API documentation in Chinese, describing WebSocket-based streaming audio synthesis
- **translate.txt**: Text completion API example using MiniMax AI service with Python requests

## Key Files

- `t2a.txt`: Complete WebSocket API documentation for text-to-speech synthesis including connection setup, task management, and audio output handling
- `translate.txt`: Python example for streaming chat completion using MiniMax API with authentication and response parsing

## API Integration Notes

The codebase demonstrates integration with two different AI services:
1. **Text-to-Speech Service**: WebSocket-based streaming audio synthesis with support for 300+ voices, audio format customization, and real-time streaming
2. **Text Completion Service**: HTTP-based chat completion with streaming responses using the MiniMax abab6.5s-chat model

Both services require API key authentication via environment variables or Bearer tokens.