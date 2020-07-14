from aiohttp import web

app = web.Application()


async def control(request):
    print(request.query)
    return web.Response(text=str(request.query))

app.router.add_get('/control', control)


# context = SSLContext(PROTOCOL_TLSv1_2)
# context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)


def main():
    try:
        web.run_app(app, host='0.0.0.0', port=8443,
                    # ssl_context=context,  # TODO: Uncomment me
                    )
    finally:
        print('Завершение приложения')


if __name__ == '__main__':
    main()
