import pandas as pd
import os
# pd.read_csv("path_to_csv")

# raw_data = pd.DataFrame(
#     [
#         {"repo":"mall","module":"mall-common","depth":2,"mmP":3,"mMP":10,"MMP":20},
#         {"repo":"mall","module":"mall-common","depth":3,"mmP":1,"mMP":2,"MMP":3},
#         {"repo":"mall","module":"mall-common","depth":4,"mmP":0,"mMP":0,"MMP":0},
#         {"repo":"mall","module":"mall-security","depth":2,"mmP":1,"mMP":2,"MMP":3},
#         {"repo":"mall","module":"mall-security","depth":3,"mmP":0,"mMP":0,"MMP":0},
#         {"repo":"shell","module":"shell-security","depth":2,"mmP":1,"mMP":2,"MMP":3},
#         {"repo":"shell","module":"shell-security","depth":3,"mmP":0,"mMP":0,"MMP":0},
#     ],
# )

raw_data = pd.read_csv(os.path.join("data","rq3_module_api_count.csv"))

# summary_data = pd.DataFrame(columns=["repo", "depth", "mmP", "mMP", "MMP"])
# for repo in raw_data["repo"].unique():
#     # repo_mask = raw_data[raw_data["repo"] == repo]
#     selected_data = raw_data[raw_data["repo"] == repo]
#     for depth in selected_data["depth"].unique():
#         summary_data = pd.concat([summary_data, pd.DataFrame([{
#             "repo":repo,
#             "depth":depth,
#             "mmP":selected_data[selected_data["depth"] == depth]["mmP"].sum(),
#             "mMP":selected_data[selected_data["depth"] == depth]["mMP"].sum(),
#             "MMP":selected_data[selected_data["depth"] == depth]["MMP"].sum(),
#         }])], ignore_index=True)

# summary_data.to_csv("./aggregation.csv")

summary_data = pd.DataFrame(columns=["depth", "mmP", "mMP", "MMP"])
for depth in raw_data["depth"].unique():
    summary_data = pd.concat([summary_data, pd.DataFrame([{
        # "repo":repo,
        "depth":depth,
        "mmP":raw_data[raw_data["depth"] == depth]["mmP"].sum(),
        "mMP":raw_data[raw_data["depth"] == depth]["mMP"].sum(),
        "MMP":raw_data[raw_data["depth"] == depth]["MMP"].sum(),
    }])], ignore_index=True)

summary_data.to_csv(os.path.join("data","rq3_aggregation.csv"), index=False)