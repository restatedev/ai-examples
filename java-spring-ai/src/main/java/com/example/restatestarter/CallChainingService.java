package com.example.restatestarter;

import dev.restate.sdk.Context;
import dev.restate.sdk.annotation.Handler;
import dev.restate.sdk.springboot.RestateService;
import org.springframework.ai.chat.client.ChatClient;



@RestateService
public class CallChainingService {
  /*
  Example prompt:
    Q3 Performance Summary:
    Our customer satisfaction score rose to 92 points this quarter.
    Revenue grew by 45% compared to last year.
    Market share is now at 23% in our primary market.
    Customer churn decreased to 5% from 8%.
  */
  record Prompt(
          String text) {}

  private final ChatClient chatClient;

  public CallChainingService(ChatClient.Builder chatClientBuilder) {
    this.chatClient = chatClientBuilder
            .build();
  }

  @Handler
  public String run(Context ctx, Prompt prompt) {

    // Step 1: Extract metrics from the input text
    String result = ctx.run("Extract metrics", String.class,
            () -> chatClient
                    .prompt("Extract only the numerical values and their associated metrics from the text." +
                            "Format each as 'metric name: metric' on a new line.")
                    .user(prompt.text())
                    .call()
                    .content()
    );

    String result2 = ctx.run("Sort metrics", String.class,
            () -> chatClient
                    .prompt("Sort all lines in descending order by numerical value.")
                    .user(result)
                    .call()
                    .content()
    );

    return ctx.run("Format as table", String.class,
            () -> chatClient
                    .prompt("Format the sorted data as a markdown table with columns 'Metric Name' and 'Value'.")
                    .user(result2)
                    .call()
                    .content()
    );
  }
}


