using System;
using System.Threading;
using System.Threading.Tasks;
using MassTransit;
using MassTransit.Util;

namespace dotnetapp
{
    public static class Program
    {
        private static ManualResetEventSlim _done = new ManualResetEventSlim(false);
        private static IBusControl _bus;

        public static void Main(string[] args)
        {
            Task.Run(() => MainAsync(args)).Wait();
        }

        public static async Task MainAsync(string[] args)
        {
            var rabbitmqUri = Environment.GetEnvironmentVariable("RABBITMQ_URI");

            using (var cts = new CancellationTokenSource())
            {
                Action Shutdown = () =>
                {
                    if (!cts.IsCancellationRequested)
                    {
                        Console.WriteLine("Application is shutting down...");
                        _bus.Stop();
                        cts.Cancel();
                    }
                    _done.Wait();
                };

                Console.CancelKeyPress += (sender, eventArgs) =>
                {
                    Shutdown();
                    eventArgs.Cancel = true;
                };

                _bus = MassTransit.Bus.Factory.CreateUsingRabbitMq(cfg =>
                {
                    cfg.Host("rabbitmq", "/", h =>
                    {
                        h.Username("user");
                        h.Password("user");
                    });

                    cfg.ReceiveEndpoint("my_queue", endpoint =>
                    {
                        endpoint.Handler<MyMessage>(async context =>
                        {
                            await Console.Out.WriteLineAsync($"Received: {context.Message.Value}");
                        });
                    });

                    cfg.ReceiveEndpoint("second_endpoint", endpoint =>
                    {
                        endpoint.Handler<MyMessage>(async context =>
                        {
                            await Console.Out.WriteLineAsync($"New msg on second endpoint: {context.Message.Value}");
                        });
                    });
                });

                await Console.Out.WriteLineAsync("Application is starting...");
                await Console.Out.WriteLineAsync($"Connecting to {rabbitmqUri}");
                
                var numberOfRetries = 4;

                while(true){
                    numberOfRetries--;

                    try {
                        await _bus.StartAsync(cts.Token);
                        break;
                    }
                    catch {
                        await Console.Out.WriteLineAsync("Couldn't started bus properly - exception !");
                        if (numberOfRetries == 0)
                            throw;
                    }
                }

                _done.Set();

                while(!cts.IsCancellationRequested)
                {
                    try{
                        var sendEndpoint = await _bus.GetSendEndpoint(new Uri("queue:startTask"));

                        await sendEndpoint.Send(new MyMessage { Value = $"Hello, World [{DateTime.Now}]" }, cts.Token);
                        await Task.Delay(5000);
                    }
                    catch {
                    }
                }
            }
        }
    }

    public class MyMessage
    {
        public string Value { get; set; }
    }
}
