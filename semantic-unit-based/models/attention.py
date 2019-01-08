import torch
import torch.nn as nn
import torch.nn.init as init


class luong_attention(nn.Module):

    def __init__(self, hidden_size, emb_size, pool_size=0):
        super(luong_attention, self).__init__()
        self.hidden_size, self.emb_size, self.pool_size = hidden_size, emb_size, pool_size
        self.linear_in = nn.Linear(hidden_size, hidden_size)
        if pool_size > 0:
            self.linear_out = maxout(2*hidden_size + emb_size, hidden_size, pool_size)
        else:
            self.linear_out = nn.Sequential(nn.Linear(2*hidden_size + emb_size, hidden_size), nn.SELU(), nn.Linear(hidden_size, hidden_size), nn.Tanh())
        self.softmax = nn.Softmax(dim=1)

    def init_context(self, context):
        self.context = context.transpose(0, 1)

    def forward(self, h, x):
        gamma_h = self.linear_in(h).unsqueeze(2)    # batch * size * 1
        weights = torch.bmm(self.context, gamma_h).squeeze(2)   # batch * time
        weights = self.softmax(weights)   # batch * time
        c_t = torch.bmm(weights.unsqueeze(1), self.context).squeeze(1) # batch * size
        output = self.linear_out(torch.cat([c_t, h, x], 1))

        return output, weights


class luong_gate_attention(nn.Module):
    
    def __init__(self, hidden_size, emb_size, prob=0.2):
        super(luong_gate_attention, self).__init__()
        self.hidden_size, self.emb_size = hidden_size, emb_size
        self.linear_in_conv = nn.Linear(hidden_size, hidden_size)
        self.linear_out_conv = nn.Linear(2*hidden_size, hidden_size)
        self.selu_out_conv = nn.Sequential(nn.SELU())
        self.linear_in = nn.Linear(hidden_size, hidden_size)
        self.linear_out = nn.Linear(2*hidden_size, hidden_size)
        self.selu_out = nn.Sequential(nn.SELU())
        self.softmax = nn.Softmax(dim=1)

    def init_context(self, context):
        self.context = context.transpose(0, 1)

    def forward(self, h, conv):
        gamma_h = self.linear_in_conv(h).unsqueeze(2)
        weights = torch.bmm(conv, gamma_h).squeeze(2)
        weights = self.softmax(weights)
        c_t_conv = torch.bmm(weights.unsqueeze(1), conv).squeeze(1)
        output_conv = self.selu_out_conv(self.linear_out_conv(torch.cat((h, c_t_conv), -1)))

        gamma_h = self.linear_in(output_conv).unsqueeze(2)
        weights = torch.bmm(self.context, gamma_h).squeeze(2)
        weights = self.softmax(weights)
        c_t = torch.bmm(weights.unsqueeze(1), self.context).squeeze(1)
        output = self.selu_out(self.linear_out(torch.cat([output_conv, c_t], -1)))

        output = output_conv + output

        return output, weights


class bahdanau_attention(nn.Module):

    def __init__(self, hidden_size, emb_size, pool_size=0):
        super(bahdanau_attention, self).__init__()
        self.linear_encoder = nn.Linear(hidden_size, hidden_size)
        self.linear_decoder = nn.Linear(hidden_size, hidden_size)
        self.linear_v = nn.Linear(hidden_size, 1)
        self.linear_r = nn.Linear(hidden_size*2+emb_size, hidden_size*2)
        self.hidden_size = hidden_size
        self.emb_size = emb_size
        self.softmax = nn.Softmax(dim=1)
        self.tanh = nn.Tanh()

    def init_context(self, context):
        self.context = context.transpose(0, 1)

    def forward(self, h, x):
        gamma_encoder = self.linear_encoder(self.context)           # batch * time * size
        gamma_decoder = self.linear_decoder(h).unsqueeze(1)    # batch * 1 * size
        weights = self.linear_v(self.tanh(gamma_encoder+gamma_decoder)).squeeze(2)   # batch * time
        weights = self.softmax(weights)   # batch * time
        c_t = torch.bmm(weights.unsqueeze(1), self.context).squeeze(1) # batch * size
        r_t = self.linear_r(torch.cat([c_t, h, x], dim=1))
        output = r_t.view(-1, self.hidden_size, 2).max(2)[0]

        return output, weights


class maxout(nn.Module):

    def __init__(self, in_feature, out_feature, pool_size):
        super(maxout, self).__init__()
        self.in_feature = in_feature
        self.out_feature = out_feature
        self.pool_size = pool_size
        self.linear = nn.Linear(in_feature, out_feature*pool_size)

    def forward(self, x):
        output = self.linear(x)
        output = output.view(-1, self.out_feature, self.pool_size)
        output = output.max(2)[0]

        return output
