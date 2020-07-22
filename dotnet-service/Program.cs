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
            using (var cts = new CancellationTokenSource())
            {

                _bus = MassTransit.Bus.Factory.CreateUsingRabbitMq(cfg =>
                {
                    cfg.Host("localhost", "/", h =>
                    {
                        h.Username("user");
                        h.Password("user");
                    });

                    cfg.ReceiveEndpoint("updateTask", endpoint =>
                    {
                        endpoint.Handler<UpdateTaskCounter>(async context =>
                        {
                            await Console.Out.WriteLineAsync($" [x] Received node {context.Message.nodeId} update, counter: {context.Message.counter}");

                        });
                    });

                    cfg.ReceiveEndpoint("updateStatus", endpoint =>
                    {
                        endpoint.Handler<UpdateTaskCounter>(async context =>
                        {
                            await Console.Out.WriteLineAsync($" [x] Received update status message");

                        });
                    });
                });

                await Console.Out.WriteLineAsync("Service is starting...");
                await Console.Out.WriteLineAsync($"Connecting to rabbitmq broker");
                
                var numberOfRetries = 4;

                while(true){
                    numberOfRetries--;

                    try {
                        await _bus.StartAsync(cts.Token);
                        break;
                    }
                    catch {
                        await Console.Out.WriteLineAsync("Couldn't started bus properly - exception !");

                        if (numberOfRetries == 0) throw;
                    }
                }

                _done.Set();

                while(!cts.IsCancellationRequested)
                {
                    try{
                        var startTaskEp = await _bus.GetSendEndpoint(new Uri("queue:startTask"));
                        var endTaskEp = await _bus.GetSendEndpoint(new Uri("queue:endTask"));
                        var nodesStatusEp = await _bus.GetSendEndpoint(new Uri("queue:nodesStatus"));

                        await Console.Out.WriteLineAsync("Sending task start request");
                        await startTaskEp.Send(new TaskRequest { nodeId = "123", taskId = 123 }, cts.Token);
                        await Task.Delay(30000);

                        await Console.Out.WriteLineAsync("Sending task end request");
                        await endTaskEp.Send(new TaskRequest { taskId = 123}, cts.Token);
                        await Task.Delay(15000);
                    }
                    catch {}
                }
            }
        }
    }

    public class TaskRequest
    {
        public string nodeId { get; set; }
        public int taskId { get; set; } 
    }

    public class UpdateTaskCounter
    {
        public string nodeId { get; set; }
        public int taskId { get; set; }
        public int counter { get; set; }
    }

    public class UpdateNodeStatus
    {
        public string nodeId { get; set; }
        public bool isActive { get; set; }
    }
}
